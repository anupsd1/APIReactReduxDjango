from django.conf import settings
from django.core.mail import send_mail

from rest_framework import generics, permissions, viewsets, status, mixins
from rest_framework.response import Response

from requests.exceptions import HTTPError
# The following import and then adding it to authentication classes is very important. Without this:
# the error was Authentication credentials were not provided.
# Took 24 hours to figure this out
from django.contrib.auth import login
from rest_framework.exceptions import PermissionDenied
from knox.auth import TokenAuthentication
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.settings import api_settings
from knox.models import AuthToken
from knox.settings import knox_settings
from rest_framework.serializers import DateTimeField
from django.utils import timezone
from pprint import pprint
from re import sub
from .models import LocalUser, GmailAccount, UserProfile
from django.shortcuts import get_object_or_404
from .serializers import (
                        UserSerializer,
                          RegisterSerializer,
                          LoginSerializer,
                          SocialSerializer,
                          ChangePasswordSerializer,
                        PremiumUpdateSerializer,
                        UserProfileSerializer,
                        GoogleAccountSerializer,
                        UpdateEmailSerializer,
                        # ForgotPasswordSerializer,
                        CheckTokenSerializer,
                          )


from social_django.utils import load_strategy, load_backend
from social_core.backends.oauth import BaseOAuth2
from social_core.exceptions import MissingBackend, AuthTokenError, AuthForbidden


# The following is very important, otherwise django's basic token authentication is used
# authentication_classes = (
#         TokenAuthentication,
#     )
# IMPORTANT!!-
# ANY TYPE OF TOKEN AUTHENTICATION CANNOT BE USED WITH THE BROWSEABLE DJANGO API


# Register API
class RegisterAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    authentication_classes = (
        TokenAuthentication,
    )

    # def get_serializer_context(self):
    #
    #     # print("FROM SERIALIZER CONTEXT = " + pprint(vars(self.request)))
    #     return {'request': self.request}

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # HERE the user object returned is actually of LocalUser type only
        # because we initialized the model to LOCALUSER in serializers.py
        user = serializer.save()

        fortoken = LocalUser.objects.get(profile_id=user)

        # send_mail(subject, message, from_email, to_list, fail_silently=True)

        subject = "Welcome to FootBuys!!"
        message = "Hi " + user.first_name + ", \nThank you for registering with us. Glad to have you with us.\n\n\n\n\n\n\n\n This is an autogenerated email. Please do not try to revert back"
        from_mail = settings.EMAIL_HOST_USER
        to_list = [fortoken.email, settings.EMAIL_HOST_USER]

        send_mail(subject, message, from_mail, to_list, fail_silently=True)

        return Response({
            "user": UserProfileSerializer(user, context=self.get_serializer_context()).data,

            # In the video it was :
            #     "token": AuthToken.objects.create(user)
            # which gave an error.
            # Answer-
            # The Token.objects.create returns a tuple (instance, token). So in order to get token use the index 1
            # "token": AuthToken.objects.create(user)[1]

            "token": AuthToken.objects.create(fortoken)[1]
        })


# Login API
class LoginAPI(generics.GenericAPIView):
    # login_url = 'api/auth/login/'
    print("BEFORE SERIALIZER CLASS")
    # permission_classes = [
    #     permissions.IsAuthenticated,
    # ]

    authentication_classes = (
        TokenAuthentication,
    )

    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        print("REQUEST.DATA = " + str(request.data))
        serializer = self.get_serializer(data=request.data)
        # serializer = self.serializer_class(data=request.data, context={'request': request})
        print("BEFORE IS_VALID IS CALLED! ")
        serializer.is_valid(raise_exception=True)

        print(str(serializer))

        # was written as
        # user = serializer.validate_data
        # which gave an error
        user = serializer.validated_data
        userprofile = UserProfile.objects.get(localuser=user)
        # login(request, user)
        return Response({
            "user": UserProfileSerializer(userprofile, context=self.get_serializer_context()).data,
            # "token": AuthToken.objects.create(user)[1]
            "token": AuthToken.objects.create(user=user)[1],
            # "token": serializer.serialize('json', AuthToken.objects.create(user=user))
            # "mytoken": AuthToken.objects.create(user=user)
        })


# Get User API
# class UserAPI(
#                 viewsets.GenericViewSet,
#                 viewsets.mixins.ListModelMixin,
#                 viewsets.mixins.RetrieveModelMixin,
#                 viewsets.mixins.DestroyModelMixin):

class UserAPI(generics.RetrieveAPIView):

    permission_classes = [

        permissions.IsAuthenticated,
        # permissions.AllowAny,
    ]

    authentication_classes = (
        TokenAuthentication,
    )

    queryset = UserProfile.objects.all()

    serializer_class = UserProfileSerializer

    def get_queryset(self):
        return UserProfile.objects.filter(localuser=self.request.user)

    def get_object(self):
        return UserProfile.objects.get(localuser=self.request.user)


class UserUpdateAPI(generics.RetrieveUpdateAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    authentication_classes = (
        TokenAuthentication,
    )

    # queryset = LocalUser.objects.all()
    serializer_class = PremiumUpdateSerializer

    # queryset = LocalUser.objects.all()

    def get_queryset(self):
        # qs = LocalUser.objects.filter(username=self.request.user)
        # profile_id = (qs[0].profile_id)
        # print("PROFILE ID = " + profile_id)
        # return UserProfile.objects.filter(localuser=qs[0])
        # print("QS 2 = "+str(qs2))
        # return qs2[0]
        return UserProfile.objects.filter(localuser=self.request.user)

        # return qs2
        # print(qs2[0])
        # return qs2[0]
    # def get_object(self, queryset=None):
    #     return self.request.user
        # return obj

    def get_object(self):
        return UserProfile.objects.get(localuser=self.request.user)

    def update(self, request, *args, **kwargs):
        # print(request['header'])
        serializer = self.get_serializer(self.get_object(), data=request.data)
        print("BEFORE SERIALIZER IS VALID---")
        serializer.is_valid(raise_exception=True)
        print("SERIALIZEER IS VALID")
        user = serializer.save()
        print(UserProfileSerializer(user, context=self.get_serializer_context()).data)
        return Response({
            "user": UserProfileSerializer(self.get_object(), context=self.get_serializer_context()).data,

        })


class ChangePasswordAPI(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [
        permissions.IsAuthenticated
    ]

    authentication_classes = (
        TokenAuthentication,
    )

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            checkpass = user.check_password(serializer.data.get("old_password"))
            # print("CHECKPASS==="+checkpass)
            if not checkpass:
                response = PermissionDenied("Wrong password")
                print(response)
                raise response
            user.set_password(serializer.data.get("new_password"))
            user.save()
            return Response("Successfully changed. Please Login again with the new password ", status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Forgot password RESET
class ForgotPasswordAPI(generics.UpdateAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    authentication_classes = (
        TokenAuthentication,
    )

    # serializer_class = ForgotPasswordSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_context(self):
        return {"user": self.request.user}

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            return Response("IT IS VALID")
        else:
            return Response("INVALID !!")


class CheckTokenAPI(generics.UpdateAPIView):
    serializer_class = CheckTokenSerializer
    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            checkpass = user.check_password(serializer.data.get("old_password"))
            # print("CHECKPASS==="+checkpass)
            if not checkpass:
                response = PermissionDenied("Wrong password")
                print(response)
                raise response
            user.set_password(serializer.data.get("new_password"))
            user.save()
            return Response("Successfully changed. Please Login again with the new password ", status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeEmailView(generics.UpdateAPIView):
    serializer_class = UpdateEmailSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    queryset = LocalUser.objects.all()

    authentication_classes = (
        TokenAuthentication,
    )

    def get_object(self):
        return self.request.user

    # IMPORTANT WHEN YOU WANT TO PASS ADDITIONAL PARAMATERS TO THE SERIALIZER
    # HERE I HAVE DONE IT TO VALIDATE CURRENT USER'S EMAIL
    def get_serializer_context(self):
        return {"user": self.get_object()}

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        profile_user = UserProfile.objects.get(localuser=user)

        print("PROFILE = " + str(profile_user))
        try:
            gmail_id = GmailAccount.objects.get(user_profile_id=profile_user)
            return Response({
                "error": "Invalid credentials",
                "details": "Cannot change from gmail"
            }, status=status.HTTP_400_BAD_REQUEST)
        except GmailAccount.DoesNotExist:
            # serializer = self.get_serializer(data=request.data)
            serializer = self.get_serializer(self.get_object(), data=request.data)
            # print("SERIALIZER = "+str(serializer))
            serializer.is_valid(raise_exception=True)
            # new_email = serializer.validated_data['email']
            new_user = serializer.save()
            if new_user:
                # print("NEW EMAIL IS = " + new_email)
                # updated_local_user = user.update(email=new_email)
                # user.save()
                # if updated_local_user:
                #     print("NOW UPDATED USER = "+str(user))
                #     print("NOW UPDATED EMAIL = "+str(user.email))
                print("NEW EMAIL = "+str(new_user.email))
                return Response({
                    "error": "Invalid credentials",
                    "details": "OH SO YOU CAN CHANGE NOW"
                }, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = LocalUser.objects.all()
    serializer_class = UserSerializer

    authentication_classes = (
        TokenAuthentication,
    )

    # print(permissions.IsAuthenticated)

    def retrieve(self, request, pk=None):
        print("User is "+self.request.user)


class SocialLoginView(generics.GenericAPIView):
    serializer_class = SocialSerializer
    permission_classes = [
        permissions.AllowAny
    ]

    authentication_classes = (
        TokenAuthentication,
    )

    # def get_existing_user(self, userprofile):
    #     return LocalUser.objects.filter(profile_id=userprofile)

    def post(self, request):

        # Authenticate through provider and access_token
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.data.get('provider', None)
        user_id = serializer.data.get('user_id')

        qs = GmailAccount.objects.select_related('user_profile_id').filter(gmail_id=user_id)
        if qs.exists():
            # print("EXISTS? = "+qs.user_profile_id_id)
            print("THIS IS IT- "+str(qs[0].user_profile_id))
            userprofile = qs[0].user_profile_id
            # user = self.get_object(userprofile)
            user = LocalUser.objects.get(profile_id=userprofile)

            return Response({
                "user": UserProfileSerializer(userprofile, context=self.get_serializer_context()).data,
                "token": AuthToken.objects.create(user)[1]
            })
        else:
            first_name = serializer.data.get('first_name')
            last_name = serializer.data.get('last_name')
            email = serializer.data.get('email')
            newuser = UserProfile.objects.create(first_name=first_name, last_name=last_name, email=email)
            newacc = GmailAccount.objects.create(gmail_id=user_id, user_profile_id=newuser)
            # print("New account" + str(newacc[0].user_profile_id))
            # updateUser = LocalUser.objects.update(profile_id=newuser)
            updateUser ='xyz'
            print("NEW ACCOUNT IS "+str(newacc))
            # print("UPDATED USER?? "+updateUser[0])

        strategy = load_strategy(request)
        print("updated user = "+updateUser)
        try:
            backend = load_backend(strategy=strategy, name=provider, redirect_uri=None)
            print("DID YOU GET BACKND = "+str(backend))
        except:
            return Response(
                {
                    'error': "Please provide a valid provider"
                },
                status=status.HTTP_400_BAD_REQUEST)

        try:
            if isinstance(backend, BaseOAuth2):
                access_token = serializer.data.get('access_token')
                print("DID YOU GET ACCESS TOKEN??"+access_token)
                user = backend.do_auth(access_token)
                print("USER??!?!!="+str(user))
        except HTTPError as error:
            return Response({
                'error': {
                    'access_token': "Invalid Token",
                    "details": str(error)
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        except AuthTokenError as error:
            return Response({
                "error": "Invalid credentials",
                "details": str(error)
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            authenticated_user = backend.do_auth(access_token, user=user)

        except HTTPError as error:
            return Response({
                "error": "Invalid token",
                "details": str(error)
            }, status=status.HTTP_400_BAD_REQUEST)

        except AuthForbidden as error:
            return Response({
                "error": "Invalid token",
                "details": str(error)
            }, status=status.HTTP_400_BAD_REQUEST)

        if authenticated_user and authenticated_user.is_active:
            # generate Knox token
            login(request, authenticated_user)
            data = {
                "token": AuthToken.objects.create(user)[1]
            }

            # user.update(profile_id=newuser)
            updateUser = LocalUser.objects.filter(username=user)
            updateUser.update(profile_id=newuser)
            print("USER TO UPDATE = "+str(updateUser))



            user_id = serializer.data.get('user_id')
            qs = GmailAccount.objects.select_related('user_profile_id').filter(gmail_id=user_id)
            if qs.exists():
                # print("EXISTS? = "+qs.user_profile_id_id)
                print("THIS IS IT- " + str(qs[0].user_profile_id))
                userprofile = qs[0].user_profile_id
                # user = self.get_object(userprofile)
                user = LocalUser.objects.get(profile_id=userprofile)

                return Response({
                    "user": UserProfileSerializer(userprofile, context=self.get_serializer_context()).data,
                    "token": AuthToken.objects.create(user)[1]
                })
            else:
                return Response({
                    "error": "An error occured",
                    "details": "An error occured"
                }, status=status.HTTP_400_BAD_REQUEST)


class GoogleAPI(generics.RetrieveAPIView):

    permission_classes = [

        permissions.IsAuthenticated,
        # permissions.AllowAny,
    ]

    authentication_classes = (
        TokenAuthentication,
    )

    queryset = GmailAccount.objects.all()

    serializer_class = GoogleAccountSerializer

    def get_queryset(self):
        return LocalUser.objects.filter(user=self.request.user)

    def get_object(self):
        return self.request.user



# class SocialLoginView(generics.GenericAPIView):
#     authentication_classes = (
#         TokenAuthentication,
#     )
#
#     serializer_class = SocialSerializer
#
#     def post(self, request, *args, **kwargs):
#         print("inside post")
#         print(request.data)
#         serializer = self.get_serializer(data=request.data)
#         # serializer = self.serializer_class(data=request.data, context={'request': request})
#         print("GOT SERIALIZER? ")
#         serializer.is_valid(raise_exception=True)
#         print("Done validation? ")
#
#
#         # login(request, user)
#         return Response({
#             "user": UserSerializer(user, context=self.get_serializer_context()).data,
#             # "token": AuthToken.objects.create(user)[1]
#             "token": AuthToken.objects.create(user=user)[1],
#             # "token": serializer.serialize('json', AuthToken.objects.create(user=user))
#             # "mytoken": AuthToken.objects.create(user=user)
#         })
