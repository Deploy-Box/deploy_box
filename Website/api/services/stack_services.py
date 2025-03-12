from ..models import Stacks
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from ..serializers.stacks_serializer import StacksSerializer


def get_stacks(request: Request, stack_id: str = None) -> Response:
    user = request.user

    if stack_id:
        try:
            stack = Stacks.objects.get(id=stack_id, user=user)
            return Response({"data": stack}, status=status.HTTP_200_OK)
        except Stacks.DoesNotExist:

            return Response({"error": "Stack Not Found"}, status.HTTP_404_NOT_FOUND)
    else:
        stacks = user.stacks_set.all()
        serializer = StacksSerializer(stacks, many=True)
        return Response({"data": serializer.data}, status.HTTP_200_OK)


def add_stack(request: Request) -> Response:
    user = request.user
    stack_type = request.data.get("type")
    variant = request.data.get("variant")
    version = request.data.get("version")

    if not stack_type or not variant or not version:
        return Response(
            {"error": "Type, variant, and version are required."},
            status.HTTP_400_BAD_REQUEST,
        )

    if Stacks.objects.filter(
        user=user, type=stack_type, variant=variant, version=version
    ).exists():
        return Response({"error": "Stack already exists"}, status.HTTP_400_BAD_REQUEST)

    Stacks.objects.create(user=user, type=stack_type, variant=variant, version=version)
    return Response({"message": "Stack added successfully"}, status.HTTP_201_CREATED)


def update_stack(request: Request, stack_id: str) -> Response:
    if not stack_id:
        return Response(
            {"error": "Stack ID is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    stack = get_stacks(request, stack_id)
    if not stack:
        return Response({"error": "Stack not found."}, status=status.HTTP_404_NOT_FOUND)

    stack_type = request.data.get("type", stack.type)
    variant = request.data.get("variant", stack.variant)
    version = request.data.get("version", stack.version)

    stack.type = stack_type
    stack.variant = variant
    stack.version = version
    stack.save()

    return Response({"message": "Stack updated successfully"}, status.HTTP_200_OK)
