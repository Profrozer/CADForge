"""Sandbox harness — runs AI-generated CadQuery code in an isolated subprocess.

Usage:  python -I harness.py <code_file> <out_dir>

Prints a single JSON result after a marker line so caller output parsing is
immune to anything the generated code prints. Network access is disabled
in-process before the user code runs; the parent enforces the hard timeout.

Failure kinds: python_error | geometry_invalid | no_result | export_error
"""

import json
import sys
import traceback

RESULT_MARKER = "===CADFORGE_RESULT==="


def emit(result: dict) -> None:
    sys.stdout.flush()
    print(RESULT_MARKER)
    print(json.dumps(result))
    sys.exit(0)


def fail(kind: str, error: str) -> None:
    emit({"ok": False, "kind": kind, "error": error[-4000:]})


def disable_network() -> None:
    import socket

    def _blocked(*args, **kwargs):
        raise RuntimeError("Network access is disabled inside the CAD sandbox.")

    # Must stay a class: ssl subclasses socket.socket at import time.
    class _BlockedSocket(socket.socket):
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Network access is disabled inside the CAD sandbox.")

    socket.socket = _BlockedSocket      # type: ignore[misc]
    socket.create_connection = _blocked
    socket.getaddrinfo = _blocked       # type: ignore[assignment]


def main() -> None:
    code_file, out_dir = sys.argv[1], sys.argv[2]
    disable_network()

    import cadquery as cq
    from cadquery import exporters

    with open(code_file, encoding="utf-8") as f:
        code = f.read()

    captured = []

    def show_object(obj, *args, **kwargs):
        captured.append(obj)

    namespace = {
        "__name__": "__cadforge__",
        "cq": cq,
        "cadquery": cq,
        "show_object": show_object,
    }
    try:
        exec(compile(code, "generated_part.py", "exec"), namespace)
    except Exception:
        fail("python_error", traceback.format_exc())

    # Locate the produced object: `result` var, show_object capture, or any
    # CadQuery object left in the namespace.
    obj = namespace.get("result")
    if obj is None and captured:
        obj = captured[-1]
    if obj is None:
        for value in reversed(list(namespace.values())):
            if isinstance(value, (cq.Workplane, cq.Shape, cq.Assembly)):
                obj = value
                break
    if obj is None:
        fail("no_result", "The code ran but did not assign a solid to a variable "
                          "named `result` (and called no show_object).")

    try:
        if isinstance(obj, cq.Assembly):
            shape = obj.toCompound()
        elif isinstance(obj, cq.Workplane):
            shapes = [v for v in obj.vals() if isinstance(v, cq.Shape)]
            if not shapes:
                fail("no_result", "`result` is a Workplane with no solid on its stack.")
            shape = shapes[0] if len(shapes) == 1 else cq.Compound.makeCompound(shapes)
        elif isinstance(obj, cq.Shape):
            shape = obj
        else:
            fail("no_result", f"`result` has unsupported type {type(obj).__name__}; "
                              "assign a cq.Workplane solid.")
    except SystemExit:
        raise
    except Exception:
        fail("geometry_invalid", traceback.format_exc())

    try:
        if not shape.isValid():
            fail("geometry_invalid",
                 "OpenCASCADE reports the resulting solid is invalid (non-manifold, "
                 "self-intersecting, or a failed boolean). Rebuild with more robust "
                 "construction.")
        bb = shape.BoundingBox()
        if max(bb.xlen, bb.ylen, bb.zlen) <= 0:
            fail("geometry_invalid", "The resulting shape has a degenerate bounding box.")
    except SystemExit:
        raise
    except Exception:
        fail("geometry_invalid", traceback.format_exc())

    exports: dict = {}
    export_errors: dict = {}
    try:
        wp = cq.Workplane("XY", obj=shape)
        exporters.export(wp, f"{out_dir}/model.step")
        exports["step"] = "model.step"
        exporters.export(wp, f"{out_dir}/model.stl", tolerance=0.05, angularTolerance=0.1)
        exports["stl"] = "model.stl"
    except SystemExit:
        raise
    except Exception:
        fail("export_error", traceback.format_exc())

    # OBJ — written from the tessellation (CadQuery has no native OBJ export).
    try:
        vertices, triangles = shape.tessellate(0.05)
        with open(f"{out_dir}/model.obj", "w", encoding="utf-8") as f:
            f.write("# CADForge export\n")
            for v in vertices:
                f.write(f"v {v.x:.6f} {v.y:.6f} {v.z:.6f}\n")
            for a, b, c in triangles:
                f.write(f"f {a + 1} {b + 1} {c + 1}\n")
        exports["obj"] = "model.obj"
    except SystemExit:
        raise
    except Exception:
        export_errors["obj"] = traceback.format_exc()[-500:]

    # DXF — planar cross-section at mid-height; only meaningful for flat/sheet
    # parts, so failure just marks the format unavailable.
    try:
        z_mid = (bb.zmin + bb.zmax) / 2.0
        section = cq.Workplane("XY", obj=shape).section(z_mid)
        exporters.export(section, f"{out_dir}/model.dxf")
        exports["dxf"] = "model.dxf"
    except SystemExit:
        raise
    except Exception:
        export_errors["dxf"] = traceback.format_exc()[-500:]

    try:
        volume = float(shape.Volume())
    except Exception:
        volume = None

    emit({
        "ok": True,
        "exports": exports,
        "export_errors": export_errors,
        "stats": {
            "volume_mm3": volume,
            "bbox_mm": [round(bb.xlen, 3), round(bb.ylen, 3), round(bb.zlen, 3)],
        },
    })


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        fail("python_error", traceback.format_exc())
