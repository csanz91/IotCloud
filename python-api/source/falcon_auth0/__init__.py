# System Imports
from copy import deepcopy
from json import loads
import logging
import json

# Third-Party Imports
from falcon import HTTPBadRequest
from falcon.status_codes import HTTP_401
import jwt
from six.moves.urllib.request import urlopen

# Local Source Imports
from .__http_factory import http_error_factory
logger = logging.getLogger(__name__)

# See https://auth0.com/docs/quickstart/backend/python/01-authorization

__version__ = "1.1.0"
VERSION = __version__

__name__ = "Auth0Middleware"


class Auth0Middleware(object):
    def __init__(self, middleware_config=None, claims={"email": "email"}):
        """ Falcon Middleware for Auth0 Authorization using Bearer Tokens.

        :param auth_config: Dictionary containing configuration variables for Auth0.

            Example:
            {
                'alg': ['RS256'],
                'access_token': 'access_token', # This is optional. This variable points to the key in the Request body
                                                  that holds the access_token. If it's not provided, it defaults to
                                                  'access_token'.
                'audience': <Auth0 Client ID>,
                'domain': 'my.app.name.auth0.com', # or 'https://my.app.name.auth0.com/'
                'jwks_uri': 'https://my.app.name.auth0.com/.well-known/jwks.json'
            }
        :type auth_config: Dict[str, Union[str, Dict[str, str]]]
        :param claims_config: TODO: I'll write this once I actually get valid claims back.
        :type claims_config: Dict[]
        :param jwt_options: A configurable list of options that dictates what validation is performed (or not performed)
            when decoding the JWT. The options Dictionary takes the form of:
            {
                'verify_signature': True,
                'verify_aud': True,
                'verify_iat': True,
                'verify_exp': True,
                'verify_nbf': True,
                'verify_iss': True,
                'verify_sub': True,
                'verify_jti': True,
                'verify_at_hash': True,
                'leeway': 0
            }
        :type jwt_options: Dict[str, Union[bool, int]]
        :param digest_access_token: The Auth0 Middleware will automatically "digest", the access_token contained in the
            body of the incoming Request.
        :type digest_access_token: bool
        :param environment: Environment specification for the configuration if you have different configurations for
            different environments. If an environment is not provided, it will assume the config is in the format
            listed above.

            Example:
            {
                'dev': {
                    'alg': ['RS256'],
                    'audience': <Auth0 Client ID>,
                    'domain': 'my.dev.environment.auth0.com', # or 'https://my.dev.environment.auth0.com/'
                    'jwks_uri': 'https://my.dev.environment.auth0.com/.well-known/jwks.json'
                },
                'test': {
                    'alg': ['RS256'],
                    'audience': <Auth0 Client ID>,
                    'domain': 'my.test.environment.auth0.com', # or 'https://my.test.environment.auth0.com/'
                    'jwks_uri': 'https://my.test.environment.auth0.com/.well-known/jwks.json'
                },
                'uat': {
                    'alg': ['RS256'],
                    'audience': <Auth0 Client ID>,
                    'domain': 'my.uat.environment.auth0.com', # or 'https://my.uat.environment.auth0.com/'
                    'jwks_uri': 'https://my.uat.environment.auth0.com/.well-known/jwks.json'
                },
                'prod': {
                    'alg': ['RS256'],
                    'audience': <Auth0 Client ID>,
                    'domain': 'my.prod.environment.auth0.com', # or 'https://my.prod.environment.auth0.com/'
                    'jwks_uri': 'https://my.prod.environment.auth0.com/.well-known/jwks.json'
                }
            }
        :type environment: str
        """
        self.config = middleware_config
        self.claims = claims
        self.__environment = None
        self.__jwks = self.__create_jwks()

    @staticmethod
    def get_token_auth_header(req):
        """ Returns the value of Authorization Header in the HTTP Request.

        :param req: Request object that will be routed to an appropriate on_* responder method.
        :type req: Request

        :raises: HTTPError := HTTPUnauthorized
        """
        logger.debug("Pulling the Authorization header from the Request.")
        try:
            _auth_token = req.get_header("Authorization")
            (_bearer, _token) = _auth_token.split()

        except HTTPBadRequest:
            raise http_error_factory(
                status=HTTP_401,
                title="No 'Authorization' Header",
                description="No 'Authorization' header was present in the request.",
                href=None,
                href_text=None,
                code=None,
            )
        except ValueError:
            raise http_error_factory(
                status=HTTP_401,
                title="Improper 'Authorization' Header Formatting",
                description="The 'Authorization' header was improperly formatted.",
                href=None,
                href_text=None,
                code=None,
            )
        except AttributeError:
            logger.info("No Authorization provided.")
            raise http_error_factory(
                status=HTTP_401,
                title="No Authorization provided",
                description="The 'Authorization' header is mandatory.",
                href=None,
                href_text=None,
                code=None,
            )

        if _bearer.lower() != "bearer":
            raise http_error_factory(
                status=HTTP_401,
                title="Invalid 'Authorization' Header",
                description="Authorization header must start with Bearer.",
                href=None,
                href_text=None,
                code=None,
            )

        return _token

    def _isAuthDisabled(self, req, resource):
        try:
            authSettings = resource.auth
            methodsExcluded = authSettings.get("methodsExcluded", [])
            authDisabled = authSettings.get("authDisabled", False)
            # If the auth is disabled -> dont check
            # Or
            # If the method is the excluded list
            return authDisabled or req.method in methodsExcluded
        except AttributeError:
            pass

        return False

    def process_resource(self, req, resp, resource, *args, **kwargs):

        if not self._isAuthDisabled(req, resource):
            self.authenticate(req, resp)

    def __create_jwks(self):
        """ Creates the JSON Web Key Set from the Auth0 .well_known/jwks.json end point.

        :return: JWKS Dictionary or None if the endpoint could not be reached.
        :rtype: Union[dict, None]
        """
        logger.debug("Getting JWKS from Auth0.")
        _jwks_uri = self.config.get(self.__environment, self.config).get(
            "jwks_uri", None
        )
        _jwks_raw = urlopen(_jwks_uri).read()
        return loads(_jwks_raw) if _jwks_raw is not None else None

    def __process_claims(self, claims):
        """ Process claims returned by parsing the JWT Authorization based on the claims config.

            Example:
            {
                'email_verified': 'verified',
                'email': 'email',
                'clientID': 'id',
                'updated_at': 'updated',
                'name': 'name',
                'picture': 'avatar',
                'user_id': 'user_id',
                'nickname': 'profile_name',
                'identities': 'profiles',
                'created_at': 'created',
                'iss': 'issuer',
                'sub': 'subject',
                'aud': 'audience',
                'iat': 'issued',
                'exp': 'expires',
                'at_hash': 'hash',
                'nonce': 'its_a_secret_to_everyone'
            }

        :param claims: Decoded JWT claims
        :type claims: Dict[str, Union[bool, str, List[Dict[]], int]]
        :return: Processed claims
        :rtype: Dict[str, Union[bool, str, List[Dict[]], int]]
        """
        logger.debug("Processing decoded JWT Claims.")
        _claims = deepcopy(claims)

        if self.claims:
            _claims = {
                self.claims[claim]: value
                for claim, value in claims.items()
                if claim in self.claims
            }
            return _claims
        return {}

    def authenticate(self, req, resp):
        """ Processes the incoming request before routing it by parsing the Authorization header, and attaching the
            claims from the JWT to the req context under the key 'auth'. If a claims configuration was passed, it
            also update the keys in the claims dictionary.

        :param req: Request object that will be routed to an appropriate on_* responder method.
        :param resp: Response object that will be routed to the on_* responder.
        """

        logger.debug("Processing incoming Request.")
        if self.__jwks is None:
            logger.warning("No JWKS has been set.")
            self.__jwks = self.__create_jwks()

        _token = self.get_token_auth_header(req)
        self.verifyToken(req, _token)

    def verifyToken(self, req, _token):
        try:
            _unverified_header = jwt.get_unverified_header(_token)
        except jwt.PyJWTError:
            raise http_error_factory(
                status=HTTP_401,
                title="invalid_header",
                description="Invalid header. " "Use an RS256 signed JWT Access Token",
                href=None,
                href_text=None,
                code=None,
            )
        if _unverified_header["alg"] == "HS256":
            raise http_error_factory(
                status=HTTP_401,
                title="invalid_header",
                description="Invalid header. " "Use an RS256 signed JWT Access Token",
                href=None,
                href_text=None,
                code=None,
            )

        _rsa_key = {}
        logger.debug("Generating RSA Key.")
        for key in self.__jwks.get("keys", []):
            if key.get("kid") == _unverified_header.get("kid"):
                _rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                if _rsa_key:
                    pubkey = jwt.algorithms.RSAAlgorithm.from_jwk(
                        json.dumps(_rsa_key))
                    try:
                        _claims = jwt.decode(
                            _token,
                            pubkey,
                            algorithms=self.config.get(
                                self.__environment, self.config
                            ).get("alg", ["RS256"]),
                            audience=self.config.get(
                                self.__environment, self.config
                            ).get("audience", None),
                            issuer=self.config.get(self.__environment, self.config).get(
                                "domain", None
                            ),
                        )
                        req.context.update(
                            {"auth": self.__process_claims(_claims)})
                    except jwt.ExpiredSignatureError as e:
                        raise http_error_factory(
                            status=HTTP_401,
                            title="Expired Token",
                            description="The provided token has expired.",
                            href=None,
                            href_text=None,
                            code=None,
                        )
                    except jwt.MissingRequiredClaimError as e:
                        raise http_error_factory(
                            status=HTTP_401,
                            title="Invalid Claims",
                            description="The claims are incorrect. Please check the Audience and the Issuer.",
                            href=None,
                            href_text=None,
                            code=None,
                        )
                    except Exception as e:
                        logger.critical("UNEXPECTED EXCEPTION.", exc_info=True)
                        raise http_error_factory(
                            status=HTTP_401,
                            title="Invalid Header",
                            description="Unable to find appropriate key.",
                            href=None,
                            href_text=None,
                            code=None,
                        )


def requires_scope(req, resp, resource, params, required_scope):
    """Determines if the required scope is present in the access token
    Args:
        required_scope (str): The scope required to access the resource
    """

    _token = Auth0Middleware.get_token_auth_header(req)
    unverified_claims = jwt.get_unverified_claims(_token)
    if unverified_claims.get("scope"):
        token_scopes = unverified_claims["scope"].split()
        for token_scope in token_scopes:
            if token_scope == required_scope:
                return True

    logger.warning("User does not have the requiered scope: %s." %
                   required_scope)
    raise http_error_factory(
        status=HTTP_401,
        title="Invalid Scope",
        description="User does not have the requiered scope.",
        href=None,
        href_text=None,
        code=None,
    )
