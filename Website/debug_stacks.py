"""
Debug script to check developer specializations
Run with: Get-Content debug_stacks.py | python manage.py shell
"""

from marketplace.models import DeveloperProfile

print("=== Developer Specializations Debug ===\n")

for dev in DeveloperProfile.objects.all():
    print(f"\nDeveloper: {dev.user.username}")
    print(f"  Has specializations: {dev.specializations.exists()}")
    print(f"  Count: {dev.specializations.count()}")
    
    if dev.specializations.exists():
        print(f"  Stacks:")
        for stack in dev.specializations.all():
            print(f"    - Type: '{stack.type}' (repr: {repr(stack.type)})")
            print(f"      Name: {stack.name}")
    else:
        print(f"  (No specializations)")
