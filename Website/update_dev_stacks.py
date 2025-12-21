"""
Script to UPDATE existing developer profiles with stack specializations.
Run with: Get-Content update_dev_stacks.py | python manage.py shell
"""

from marketplace.models import DeveloperProfile
from stacks.models import PurchasableStack

# Get available stacks
mern = PurchasableStack.objects.filter(type='MERN').first()
django_stack = PurchasableStack.objects.filter(type='DJANGO').first()

print("Available stacks in database:")
for stack in PurchasableStack.objects.all().distinct('type'):
    print(f"  - {stack.type}")

print("\nUpdating developer specializations...")

# Update alex_fullstack with MERN
try:
    dev = DeveloperProfile.objects.get(user__username='alex_fullstack')
    dev.specializations.clear()
    if mern:
        dev.specializations.add(mern)
        print(f"✅ Updated {dev.user.username} with MERN")
except DeveloperProfile.DoesNotExist:
    print("❌ alex_fullstack not found")

# Update sarah_mobile_ai with MERN (as placeholder since Mobile doesn't exist)
try:
    dev = DeveloperProfile.objects.get(user__username='sarah_mobile_ai')
    dev.specializations.clear()
    if mern:
        dev.specializations.add(mern)
        print(f"✅ Updated {dev.user.username} with MERN")
except DeveloperProfile.DoesNotExist:
    print("❌ sarah_mobile_ai not found")

# Update michael_ai_vision with MERN (as placeholder)
try:
    dev = DeveloperProfile.objects.get(user__username='michael_ai_vision')
    dev.specializations.clear()
    if mern:
        dev.specializations.add(mern)
        print(f"✅ Updated {dev.user.username} with MERN")
except DeveloperProfile.DoesNotExist:
    print("❌ michael_ai_vision not found")

# Update emily_backend with Django
try:
    dev = DeveloperProfile.objects.get(user__username='emily_backend')
    dev.specializations.clear()
    if django_stack:
        dev.specializations.add(django_stack)
        print(f"✅ Updated {dev.user.username} with DJANGO")
except DeveloperProfile.DoesNotExist:
    print("❌ emily_backend not found")

# Update david_classic with Django (as placeholder since LAMP doesn't exist)
try:
    dev = DeveloperProfile.objects.get(user__username='david_classic')
    dev.specializations.clear()
    if django_stack:
        dev.specializations.add(django_stack)
        print(f"✅ Updated {dev.user.username} with DJANGO")
except DeveloperProfile.DoesNotExist:
    print("❌ david_classic not found")

print("\n✅ Update complete!")
print("\nDevelopers and their stacks:")
for dev in DeveloperProfile.objects.all():
    stacks = ", ".join([s.type for s in dev.specializations.all()])
    print(f"  • {dev.user.username}: {stacks if stacks else '(none)'}")
