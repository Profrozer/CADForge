"""Offline demo provider — exercises the full pipeline without any API key."""

from .base import Provider

BRACKET_CODE = '''\
import cadquery as cq

# Parametric L-bracket (mock demo part)
length = 80.0        # mm
width = 60.0         # mm
thickness = 5.0      # mm
hole_diameter = 6.0  # mm
hole_spacing = 40.0  # mm
corner_fillet = 3.0  # mm

base = (
    cq.Workplane("XY")
    .box(length, width, thickness, centered=(True, True, False))
    .edges("|Z")
    .fillet(corner_fillet)
)

result = (
    base.faces(">Z")
    .workplane()
    .pushPoints([(-hole_spacing / 2, 0), (hole_spacing / 2, 0)])
    .hole(hole_diameter)
)
'''

MOCK_SPEC = """\
**Part** — Flat mounting plate / L-bracket base (mock demo).

**Dimensions** — 80 mm x 60 mm, 5 mm thick.

**Features** — Two 6 mm through holes, 40 mm apart on the long axis, centered; 3 mm fillets on the four outer corners.

**Assumptions** — This is the built-in mock provider: it always produces this demo bracket regardless of the prompt. Select a real AI provider in Settings to generate your actual part."""


class MockProvider(Provider):
    name = "mock"
    label = "Mock (offline demo)"
    requires_key = False
    default_model = "mock-bracket-v1"
    static_models = ["mock-bracket-v1"]

    async def chat(self, system: str, user: str, max_tokens: int = 8000) -> str:
        return "OK"

    async def normalize(self, prompt: str, units: str = "mm") -> str:
        return MOCK_SPEC

    async def generate(self, spec: str) -> str:
        return BRACKET_CODE

    async def edit(self, prior_code: str, instruction: str) -> str:
        return prior_code + f"\n# mock edit requested: {instruction}\n"

    async def correct(self, code: str, error: str) -> str:
        return BRACKET_CODE

    async def test_key(self) -> None:
        return None
