from backend.services.email_engine import categorize_with_ai
from backend.models.template import Template

t1 = Template(project_name='Kukatpallyvhouses', is_active=True)
t2 = Template(project_name='Kondapur', is_active=True)

print(categorize_with_ai('kondapur houses', [t1, t2], ''))
