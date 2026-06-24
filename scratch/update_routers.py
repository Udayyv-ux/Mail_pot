import os
import re

def update_router(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Add import
    if "require_active_subscription" not in content:
        content = content.replace(
            "from backend.middleware.auth_middleware import require_client",
            "from backend.middleware.auth_middleware import require_client, require_active_subscription"
        )

    # We need to replace user: User = Depends(require_client) 
    # with user: User = Depends(require_active_subscription)
    # ONLY for @router.post, @router.put, @router.delete
    
    # Let's split by @router
    chunks = re.split(r'(@router\.(?:post|put|delete|get)\[.*?\]|\n@router\.(?:post|put|delete|get)\(.*?\)[\s\S]*?(?=\n@router|\Z))', content)
    
    new_content = ""
    for i, chunk in enumerate(chunks):
        if chunk.startswith('\n@router.post') or chunk.startswith('\n@router.put') or chunk.startswith('\n@router.delete'):
            # Replace in this chunk
            chunk = chunk.replace("Depends(require_client)", "Depends(require_active_subscription)")
        new_content += chunk
        
    # Wait, the regex split might be a bit flaky. 
    # Let's do a simpler approach:
    # Just replace all `Depends(require_client)` with `Depends(require_active_subscription)` 
    # inside functions decorated with @router.(post|put|delete).
    
    # Re-reading content to do a state machine approach
    lines = content.split('\n')
    new_lines = []
    in_mutating_route = False
    
    for line in lines:
        if line.startswith('@router.post') or line.startswith('@router.put') or line.startswith('@router.delete'):
            in_mutating_route = True
        elif line.startswith('@router.get'):
            in_mutating_route = False
            
        if in_mutating_route and "Depends(require_client)" in line:
            line = line.replace("Depends(require_client)", "Depends(require_active_subscription)")
            
        new_lines.append(line)
        
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('\n'.join(new_lines))

update_router(r"C:\Users\Uday\Documents\GitHub\Mail_pot\backend\routers\client_api.py")
update_router(r"C:\Users\Uday\Documents\GitHub\Mail_pot\backend\routers\templates_api.py")
print("Routers updated successfully.")
