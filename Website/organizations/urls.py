from django.urls import path
from . import views

urlpatterns = [
    path("", views.bulk_routing, name="organization_base"),
    path("<str:organization_id>/", views.specific_routing, name="get_organization"),
    path("<str:organization_id>/update_role/<str:user_id>", views.update_user, name="update_user"),
    path("<str:organization_id>/add_org_member", views.add_org_member, name="add_org_member"),
    path("<str:organization_id>/invite_new_user_to_org", views.invite_new_user_to_org, name="invite_new_user_to_org"),
    path("<str:organization_id>/remove_org_member/<str:user_id>", views.remove_org_member, name="remove_org_member"),
    path("<str:organization_id>/remove_pending_invite/<str:invite_id>", views.remove_pending_invite, name="remove_pending_invite"),
    path("<str:organization_id>/leave_organization", views.leave_organization, name="leave_organization")
]
