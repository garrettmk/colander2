import pprint as pp

import marshmallow as mm
import marshmallow.fields as mmf

from .common import OpsActor


########################################################################################################################


class DebugContext(OpsActor):
    """Displays context information."""
    public = True

    def perform(self):
        ctx = self.context
        pp.pprint(ctx.as_dict())


########################################################################################################################


class ExpireContext(OpsActor):
    """Set's an expiration on a context tree."""
    public = True

    class Schema(mm.Schema):
        """Parameter schema for CleanupContext."""
        seconds = mmf.Int(missing=60)

    def perform(self, seconds=None):
        self.context.expire(seconds)
