# Re-export all views so that `from . import views` in urls.py
# continues to resolve every name that was previously in the monolith.

from .pages import (  # noqa: F401
    home,
    stacks,
    mern_stack,
    django_stack,
    mean_stack,
    lamp_stack,
    mevn_stack,
    mobile_stack,
    llm_stack,
    ai_data_stack,
    computer_vision_stack,
    image_generation_stack,
    ai_agents_stack,
    pricing,
    profile,
    maintenance,
    still_configuring,
    subdomain_not_found,
    google_verification,
    sitemap,
    ComponentsView,
    components_view,
)

from .dashboard import (  # noqa: F401
    DashboardView,
    dashboard_view,
)

from .payments import (  # noqa: F401
    PaymentView,
    payment_view,
)

from .auth import (  # noqa: F401
    AuthView,
    auth_view,
)

from .examples import (  # noqa: F401
    ExamplesView,
    examples_view,
)
