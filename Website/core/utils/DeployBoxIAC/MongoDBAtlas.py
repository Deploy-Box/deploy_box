import os
import dotenv

dotenv.load_dotenv()

PROVIDER_NAME = "mongodbatlas"


class MongoDBAtlasDeployBoxIAC:
    def __init__(self):
        """
        Initialize the class MongoDBAtlasDeployBoxIAC:
        """
        self.public_key = os.getenv("MONGODB_ATLAS_PUBLIC_KEY")
        self.private_key = os.getenv("MONGODB_ATLAS_PRIVATE_KEY")
        self.state = {}

    def plan(self, terraform: dict, deploy_box_iac: dict, state: dict):
        self.state = state.setdefault(PROVIDER_NAME, {})

        required_providers = terraform.get("terraform", {}).setdefault(
            "required_providers", {}
        )
        required_providers.update(
            {PROVIDER_NAME: {"source": "mongodb/mongodbatlas", "version": "~> 1.4"}}
        )

        provider = terraform.get("provider", {})
        assert isinstance(provider, dict)

        resource = terraform.get("resource", {})
        assert isinstance(resource, dict)

        provider.update(
            {
                PROVIDER_NAME: {
                    "public_key": self.public_key,
                    "private_key": self.private_key,
                }
            }
        )

        mongodb_deploy_box_iac = {
            k: v for k, v in deploy_box_iac.items() if k.startswith(PROVIDER_NAME)
        }

        resource.update(mongodb_deploy_box_iac)

        return {
            "terraform": {"required_providers": required_providers},
            "provider": provider,
            "resource": resource,
        }
