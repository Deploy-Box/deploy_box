from django.shortcuts import render


KALEB_SHOWCASE_PROJECTS = [
    {
        "name": "Finishing Touch Dental Lab",
        "url": "https://finishingtouchdentallab.z13.web.core.windows.net/",
        "summary": "Dental production site with a polished local-business presentation.",
        "image": "/media/finishingtouchdentallab.png",
        "image_alt": "Finishing Touch Dental Lab homepage screenshot",
    },
    {
        "name": "Heitmeyer Concrete",
        "url": "https://heitmeyerconcrete.z13.web.core.windows.net/",
        "summary": "Contractor website built to present services, trust, and inquiry flow.",
        "image": "/media/heitmeyer.png",
        "image_alt": "Heitmeyer Concrete homepage screenshot",
    },
    {
        "name": "John Breitigam Home Improvement",
        "url": "https://johnbreitigamhomeimpro.z13.web.core.windows.net/",
        "summary": "Home improvement portfolio site focused on service discovery and lead capture.",
        "image": "/media/johnbreitigam.png",
        "image_alt": "John Breitigam Home Improvement homepage screenshot",
    },
    {
        "name": "Powell Memorial",
        "url": "https://powellmemorialprod.z20.web.core.windows.net/",
        "summary": "Memorial experience with a calm, respectful presentation for visitors.",
        "image": "/media/powellmemorial.png",
        "image_alt": "Powell Memorial homepage screenshot",
    },
    {
        "name": "Deploy Box",
        "url": "https://deploy-box.com/",
        "summary": "Flagship product site showcasing the platform and its launch-ready stack.",
        "image": "/media/deploybox.png",
        "image_alt": "Deploy Box homepage screenshot",
    },
]


def developer_home(request):
    return render(request, "developer/home.html")


def developer_detail(request, username):
    return render(request, "developer/detail.html", {"username": username})


def developer_showcase(request, username):
    if username == "kalebwbishop":
        return render(
            request,
            "developer/kalebwbishop.html",
            {"username": username, "projects": KALEB_SHOWCASE_PROJECTS, "show_navbar": True},
        )
    return render(request, "developer/showcase.html", {"username": username})
