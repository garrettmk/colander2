from .common import OpsActor


########################################################################################################################


class DebugContext(OpsActor):
    """Displays context information."""
    public = True

    def perform(self):
        ctx = self.context
        from pprint import pprint
        pprint(ctx.as_dict())
