"""
Script to seed the marketplace with sample developer profiles.
Run with: Get-Content seed_marketplace.py | python manage.py shell
"""

from accounts.models import UserProfile
from marketplace.models import DeveloperProfile
from stacks.models import PurchasableStack

# Get or create test users
def create_test_developers():
    # Create developer 1 - Full Stack MERN/MEAN Expert
    user1, _ = UserProfile.objects.get_or_create(
        username='alex_fullstack',
        defaults={
            'email': 'alex@example.com',
            'first_name': 'Alex',
            'last_name': 'Johnson'
        }
    )
    
    dev1, created = DeveloperProfile.objects.get_or_create(
        user=user1,
        defaults={
            'tagline': 'Full-Stack JavaScript & Node.js Expert',
            'bio': 'Passionate about building scalable web applications with modern JavaScript frameworks. 7+ years of experience delivering production-ready solutions using MERN, MEAN, and MEVN stacks. Expert in MongoDB, Express, React, Angular, Vue.js, and Node.js.',
            'hourly_rate': 125.00,
            'is_available': True,
            'github_url': 'https://github.com/alexjohnson',
            'linkedin_url': 'https://linkedin.com/in/alexjohnson',
        }
    )
    
    if created:
        # Add multiple stack specializations
        mern = PurchasableStack.objects.filter(type='MERN').first()
        mean = PurchasableStack.objects.filter(type='MEAN').first()
        mevn = PurchasableStack.objects.filter(type='MEVN').first()
        
        if mern:
            dev1.specializations.add(mern)
        if mean:
            dev1.specializations.add(mean)
        if mevn:
            dev1.specializations.add(mevn)
        print(f"✅ Created developer profile: {dev1}")
    
    # Create developer 2 - Mobile & AI Expert
    user2, _ = UserProfile.objects.get_or_create(
        username='sarah_mobile_ai',
        defaults={
            'email': 'sarah@example.com',
            'first_name': 'Sarah',
            'last_name': 'Chen'
        }
    )
    
    dev2, created = DeveloperProfile.objects.get_or_create(
        user=user2,
        defaults={
            'tagline': 'Mobile Development & AI Integration Specialist',
            'bio': 'Expert in cross-platform mobile development using React Native and Expo, with deep knowledge of AI/LLM integration. Built 20+ apps with millions of downloads. Specialized in bringing cutting-edge AI features to mobile applications.',
            'hourly_rate': 150.00,
            'is_available': True,
            'github_url': 'https://github.com/sarahchen',
            'website_url': 'https://sarahchen.dev',
        }
    )
    
    if created:
        mobile = PurchasableStack.objects.filter(type='Mobile').first()
        llm = PurchasableStack.objects.filter(type='LLM').first()
        ai_agents = PurchasableStack.objects.filter(type='AI-Agents').first()
        
        if mobile:
            dev2.specializations.add(mobile)
        if llm:
            dev2.specializations.add(llm)
        if ai_agents:
            dev2.specializations.add(ai_agents)
        print(f"✅ Created developer profile: {dev2}")
    
    # Create developer 3 - AI/ML/Computer Vision Expert
    user3, _ = UserProfile.objects.get_or_create(
        username='michael_ai_vision',
        defaults={
            'email': 'michael@example.com',
            'first_name': 'Michael',
            'last_name': 'Rodriguez'
        }
    )
    
    dev3, created = DeveloperProfile.objects.get_or_create(
        user=user3,
        defaults={
            'tagline': 'AI/ML Engineer & Computer Vision Expert',
            'bio': 'Specialized in Machine Learning pipelines, Computer Vision, and Generative AI. Experience with OpenAI, Anthropic, custom model deployment, OpenCV, YOLO, and Stable Diffusion. Built production AI systems processing millions of images daily.',
            'hourly_rate': 175.00,
            'is_available': True,
            'github_url': 'https://github.com/mrodriguez',
            'linkedin_url': 'https://linkedin.com/in/mrodriguez',
            'website_url': 'https://aiexperts.io',
        }
    )
    
    if created:
        ai_data = PurchasableStack.objects.filter(type='AI-Data').first()
        computer_vision = PurchasableStack.objects.filter(type='Computer-Vision').first()
        image_gen = PurchasableStack.objects.filter(type='Image-Generation').first()
        llm = PurchasableStack.objects.filter(type='LLM').first()
        
        if ai_data:
            dev3.specializations.add(ai_data)
        if computer_vision:
            dev3.specializations.add(computer_vision)
        if image_gen:
            dev3.specializations.add(image_gen)
        if llm:
            dev3.specializations.add(llm)
        print(f"✅ Created developer profile: {dev3}")
    
    # Create developer 4 - Backend Python Expert (Currently Busy)
    user4, _ = UserProfile.objects.get_or_create(
        username='emily_backend',
        defaults={
            'email': 'emily@example.com',
            'first_name': 'Emily',
            'last_name': 'Watson'
        }
    )
    
    dev4, created = DeveloperProfile.objects.get_or_create(
        user=user4,
        defaults={
            'tagline': 'Django & Python Backend Architect',
            'bio': 'Backend specialist with deep expertise in Django, PostgreSQL, and REST API design. 8 years building enterprise-grade systems. Currently working on a major fintech platform migration.',
            'hourly_rate': 140.00,
            'is_available': False,
            'github_url': 'https://github.com/ewatson',
            'linkedin_url': 'https://linkedin.com/in/emilywatson',
        }
    )
    
    if created:
        django = PurchasableStack.objects.filter(type='Django').first()
        if django:
            dev4.specializations.add(django)
        print(f"✅ Created developer profile: {dev4}")

    # Create developer 5 - Classic Web Developer
    user5, _ = UserProfile.objects.get_or_create(
        username='david_classic',
        defaults={
            'email': 'david@example.com',
            'first_name': 'David',
            'last_name': 'Miller'
        }
    )
    
    dev5, created = DeveloperProfile.objects.get_or_create(
        user=user5,
        defaults={
            'tagline': 'LAMP Stack & Legacy System Specialist',
            'bio': 'Veteran developer with 12+ years maintaining and modernizing PHP applications. Expert in WordPress, Laravel, and classic LAMP architecture. Specialized in migrating legacy systems to modern infrastructure while maintaining uptime.',
            'hourly_rate': 110.00,
            'is_available': True,
            'github_url': 'https://github.com/davidmiller',
        }
    )
    
    if created:
        lamp = PurchasableStack.objects.filter(type='LAMP').first()
        if lamp:
            dev5.specializations.add(lamp)
        print(f"✅ Created developer profile: {dev5}")

    print("\n✅ Marketplace seeding complete!")
    print(f"Total developers: {DeveloperProfile.objects.count()}")
    print("\nDevelopers by specialization:")
    for dev in DeveloperProfile.objects.all():
        stacks = ", ".join([s.type for s in dev.specializations.all()])
        status = "Available" if dev.is_available else "Busy"
        print(f"  • {dev.user.username}: {stacks} ({status})")

if __name__ == '__main__':
    create_test_developers()
