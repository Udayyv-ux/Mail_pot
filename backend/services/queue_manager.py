"""
Multi-tenant email queue manager with rate limiting and fair scheduling.
"""
import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from backend.services.email_engine import send_template_email, categorize_with_ai

@dataclass
class EmailTask:
    campaign_id: str
    client_id: str
    to_email: str
    name: str
    inquiry: str
    row_index: int
    templates: list
    smtp_config: dict
    groq_key: str
    sheet_id: str

class TenantRateLimiter:
    def __init__(self, rate_per_minute: int):
        self.rate = rate_per_minute / 60.0
        self.max_tokens = rate_per_minute
        self.tokens = float(rate_per_minute)
        self.last_refill = time.monotonic()

    async def acquire(self):
        while True:
            self._refill()
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return
            await asyncio.sleep(0.1)

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate)
        self.last_refill = now

class QueueManager:
    def __init__(self):
        self.tenant_queues = defaultdict(asyncio.Queue)
        self.rate_limiters = {}
        self.global_semaphore = asyncio.Semaphore(50)
        self.active_tenants = set()
        self.is_running = False
        self.workers = []
        self.campaign_status = {} # To support pause/resume

    def register_tenant(self, tenant_id: str, daily_limit: int):
        # Convert daily limit to an approximate per-minute limit for the burst logic
        # For simplicity, we just set a reasonable burst rate
        rate = max(10, daily_limit // 60) 
        if tenant_id not in self.rate_limiters:
            self.rate_limiters[tenant_id] = TenantRateLimiter(rate_per_minute=rate)
        self.active_tenants.add(tenant_id)

    async def enqueue(self, task: EmailTask):
        self.active_tenants.add(task.client_id)
        await self.tenant_queues[task.client_id].put(task)

    def pause_campaign(self, campaign_id: str):
        self.campaign_status[campaign_id] = "paused"
        
    def resume_campaign(self, campaign_id: str):
        self.campaign_status[campaign_id] = "running"

    async def worker(self, worker_id: int):
        from backend.database import SessionLocal
        from backend.models.campaign import Campaign, EmailLog
        from backend.services.sheets_service import update_sheet_cell
        import datetime

        while self.is_running:
            processed = False
            for tenant_id in list(self.active_tenants):
                queue = self.tenant_queues[tenant_id]
                if not queue.empty():
                    limiter = self.rate_limiters.get(tenant_id)
                    if limiter:
                        await limiter.acquire()
                    
                    task: EmailTask = await queue.get()
                    
                    if self.campaign_status.get(task.campaign_id) == "paused":
                        # Re-enqueue if paused
                        await queue.put(task)
                        queue.task_done()
                        continue

                    processed = True
                    
                    async with self.global_semaphore:
                        try:
                            # 1. Categorize
                            category = categorize_with_ai(task.inquiry, task.templates, task.groq_key)
                            
                            # Find template
                            target_template = next((t for t in task.templates if t.project_name == category), None)
                            if not target_template and task.templates:
                                target_template = task.templates[0] # Fallback
                                
                            status = "failed"
                            error_msg = "No active templates found"
                            
                            if target_template:
                                # 2. Send email
                                success = await send_template_email(task.to_email, task.name, target_template, task.smtp_config)
                                if success:
                                    status = "sent"
                                    error_msg = ""
                                    # 3. Update sheet
                                    if task.sheet_id:
                                        await update_sheet_cell(task.sheet_id, task.row_index, 4, category)
                                        await asyncio.sleep(1) # rate limit sheet API
                                        await update_sheet_cell(task.sheet_id, task.row_index, 5, "Sent")
                                else:
                                    error_msg = "SMTP delivery failed"
                            
                            # 4. Log to DB
                            async with SessionLocal() as db:
                                log = EmailLog(
                                    campaign_id=task.campaign_id,
                                    recipient_email=task.to_email,
                                    recipient_name=task.name,
                                    template_used=target_template.project_name if target_template else "",
                                    category_assigned=category,
                                    status=status,
                                    error_message=error_msg,
                                    sent_at=datetime.datetime.utcnow() if status == "sent" else None
                                )
                                db.add(log)
                                
                                # Update campaign stats
                                camp = await db.get(Campaign, task.campaign_id)
                                if camp:
                                    if status == "sent":
                                        camp.emails_sent += 1
                                    else:
                                        camp.emails_failed += 1
                                        
                                await db.commit()
                        except Exception as e:
                            print(f"Worker {worker_id} error processing task: {e}")
                        finally:
                            queue.task_done()
            
            if not processed:
                await asyncio.sleep(0.5)

    async def start_workers(self, num_workers: int = 5):
        self.is_running = True
        self.workers = [asyncio.create_task(self.worker(i)) for i in range(num_workers)]

    async def stop(self):
        self.is_running = False
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers = []

queue_manager = QueueManager()
