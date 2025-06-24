import json

from django.db import models, transaction
from django.urls import path
from django.http import HttpRequest, JsonResponse
from typing import Union, Any


class RequestableModel(models.Model):
    class Meta:
        abstract = True

    accepted_anonymous_methods = ["GET", "POST"]
    accepted_identified_methods = ["GET", "DELETE"]

    @classmethod
    def convert_model_to_json(cls, objects, expansions=None):
        """
        Serializes a queryset or list of model instances into a list of dictionaries.
        If an expansion like 'expand__chat' is specified, it will recursively serialize that related model.
        """
        if expansions is None:
            expansions = ["expand__chat"]

        data = []

        for obj in objects:
            obj_data = {}

            for field in cls._meta.fields:
                attr = getattr(obj, field.name)

                # If it's a related model (ForeignKey or OneToOneField)
                if isinstance(attr, models.Model):
                    expand_key = f"expand__{field.name}"
                    if expand_key in expansions:
                        # Recursively convert the related model to JSON
                        attr = cls.convert_model_to_json([attr], expansions=expansions)
                    else:
                        # Just include the primary key
                        attr = attr.pk

                obj_data[field.name] = attr

            data.append(obj_data)

        return data

    @classmethod
    def get_service(cls, **kwargs):
        return cls.objects.filter(**kwargs)

    @classmethod
    def post_service(cls, **kwargs):
        return cls.objects.create(**kwargs)

    @classmethod
    def delete_service(cls, **kwargs):
        cls.objects.filter(**kwargs).delete()

    @classmethod
    def handle_get_request(cls, request: HttpRequest, pk=None) -> JsonResponse:
        query_parameters = {key: value for key, value in request.GET.items()}

        cls.validate_pk(pk=pk)
        cls.validate_fields(**query_parameters)
        data = cls.get_service(**({"pk": pk} if pk else {}), **query_parameters)
        json_data = cls.convert_model_to_json(objects=data)

        return JsonResponse(data={"success": True, "data": json_data})

    @classmethod
    def handle_post_request(cls, request: HttpRequest) -> JsonResponse:
        body_parameters = json.loads(request.body)

        data = cls.post_service(**body_parameters)
        json_data = cls.convert_model_to_json(objects=[data])

        return JsonResponse(data={"success": True, "data": json_data})

    @classmethod
    def handle_delete_request(cls, request: HttpRequest, pk) -> JsonResponse:
        query_parameters = {key: value for key, value in request.GET.items()}

        cls.validate_pk(pk=pk, required=True)
        cls.validate_fields(**query_parameters)
        cls.delete_service(pk=pk)

        return JsonResponse(data={"success": True, "message": "Deletion successful"})

    @classmethod
    def pk_in_kwargs(cls, **kwargs):
        pk = cls._meta.pk
        assert pk is not None

        return kwargs.get(f"{cls._meta.model_name}_{pk.name}", None)

    @classmethod
    def validate_fields(cls, **kwargs) -> bool:
        # Get all valid field names for the model
        valid_fields = {field.name for field in cls._meta.get_fields()}

        # Check for invalid fields in kwargs
        for key in kwargs:
            if key not in valid_fields:
                raise Exception(f"{key} is not a valid field for {cls.__name__}")

        return True

    @classmethod
    def validate_pk(cls, pk, required=False) -> Union[str, None]:
        if required and not pk:
            raise Exception("Primary key not found")

        return pk

    @classmethod
    def handle_request(cls, request: HttpRequest, **kwargs) -> JsonResponse:
        try:
            with transaction.atomic():
                pk = cls.pk_in_kwargs(**kwargs)

                if pk:
                    if request.method not in cls.accepted_identified_methods:
                        raise Exception("Invalid request method")
                else:
                    if request.method not in cls.accepted_anonymous_methods:
                        raise Exception("Invalid request method")

                if request.method == "GET":
                    return cls.handle_get_request(request=request, pk=pk)
                if request.method == "POST":
                    return cls.handle_post_request(request=request)
                if request.method == "DELETE":
                    return cls.handle_delete_request(request=request, pk=pk)

                # Should not be able to get to this point
                return JsonResponse(
                    {"success": False, "message": "Invalid request method"}
                )

        except json.decoder.JSONDecodeError as e:
            return JsonResponse(
                data={"success": False, "message": "Json decode failed"}
            )

        except Exception as e:
            print("ERROR: ", str(e))
            print("ERROR TYPE", type(e))
            raise e
            return JsonResponse({"success": False, "message": str(e)}, status=400)

    @classmethod
    def get_urlpatterns(cls, baseurl):
        if baseurl:
            baseurl += "/"

        return [
            path(
                f"{baseurl}",
                cls.handle_request,
                name=f"anonymous_{cls._meta.model_name}_handler",
            ),
            path(
                f"{baseurl}<str:{cls._meta.model_name}_id>/",
                cls.handle_request,
                name=f"identified_{cls._meta.model_name}_handler",
            ),
        ]
