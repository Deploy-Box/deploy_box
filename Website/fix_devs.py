"""
Simple script to add MERN stack to ALL existing developers
Run with: Get-Content fix_devs.py | python manage.py shell
"""

from marketplace.models import DeveloperProfile
from stacks.models import PurchasableStack

mern = PurchasableStack.objects.filter(type='MERN').first()

if not mern:
    print("❌ No MERN stack found in database!")
else:
    print(f"✅ Found MERN stack: {mern.id}")
    
    for dev in DeveloperProfile.objects.all():
        dev.specializations.clear()
        dev.specializations.add(mern)
        print(f"✅ Added MERN to {dev.user.username}")
    
    print("\n=== Final Check ===")
    for dev in DeveloperProfile.objects.all():
        stacks = list(dev.specializations.values_list('type', flat=True))
        print(f"{dev.user.username}: {stacks}")
