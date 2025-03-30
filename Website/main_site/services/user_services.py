from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from api.serializers.stacks_serializer import StacksSerializer, StackDatabasesSerializer
import requests
from django.http import FileResponse
from google.cloud import storage
import os
from google.oauth2 import service_account
from django.shortcuts import get_object_or_404
import logging
from django.conf import settings
import api.utils.gcp_utils as gcp_utils
import api.utils.mongodb_utils as mongodb_utils
from api.models import StackDatabases, StackBackends, Stacks, StackFrontends
from django.db.models import F
from django.contrib.auth.models import User


#user crud
def delete_user(request, user_name):
    user = User.objects.get(username=user_name)
    user.delete()

    
