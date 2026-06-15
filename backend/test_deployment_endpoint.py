from django.test import SimpleTestCase


class GenLayerDeploymentEndpointTests(SimpleTestCase):
    def test_user_viewset_exposes_deployment_actions(self):
        from users.views import UserViewSet

        viewset = UserViewSet()

        self.assertTrue(hasattr(viewset, 'check_deployments'))
        self.assertTrue(hasattr(viewset, 'deployment_status'))

    def test_deployment_service_imports(self):
        from users.genlayer_service import GenLayerDeploymentService

        self.assertIsNotNone(GenLayerDeploymentService)
