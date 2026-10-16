"""Compile the production restore functions against both DRM API shapes."""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "driver/drivers/gpu/drm/i915/display/intel_fbdev.c"


def restore_functions():
    text = SOURCE.read_text()
    match = re.search(r"static int intel_fbdev_restore_mode\([^;]*?\)\n\{", text)
    pos, depth = match.end(), 1
    while depth:
        depth += (text[pos] == "{") - (text[pos] == "}")
        pos += 1
    helper = text[match.start():pos]
    start = text.index("#if MATEBOOK_DRM_CLIENT_RESTORE_HAS_FORCE\nstatic int intel_fbdev_client_restore")
    end = text.index("\nstatic int intel_fbdev_client_hotplug", start)
    return helper + "\n" + text[start:end]


PREFIX = r'''
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
struct drm_fb_helper { int unused; };
struct drm_device { int unused; };
struct drm_client_dev { struct drm_device *dev; };
struct intel_fbdev { struct drm_fb_helper helper; void *vma; };
struct drm_i915_private { struct { struct { struct intel_fbdev *fbdev; } fbdev; } display; };
static struct drm_i915_private device;
static int helper_ret, helper_calls, observed_force = -1, invalidations, switches;
static struct drm_i915_private *to_i915(struct drm_device *dev)
{ (void)dev; return &device; }
static void intel_fbdev_invalidate(struct intel_fbdev *fbdev)
{ (void)fbdev; ++invalidations; }
static void vga_switcheroo_process_delayed_switch(void) { ++switches; }
#if MATEBOOK_DRM_FB_HELPER_RESTORE_HAS_FORCE
static int drm_fb_helper_restore_fbdev_mode_unlocked(struct drm_fb_helper *helper, bool force)
{ (void)helper; ++helper_calls; observed_force = force; return helper_ret; }
#else
static int drm_fb_helper_restore_fbdev_mode_unlocked(struct drm_fb_helper *helper)
{ (void)helper; ++helper_calls; return helper_ret; }
#endif
struct drm_client_funcs {
#if MATEBOOK_DRM_CLIENT_RESTORE_HAS_FORCE
    int (*restore)(struct drm_client_dev *, bool);
#else
    int (*restore)(struct drm_client_dev *);
#endif
};
'''

MAIN = r'''
static const struct drm_client_funcs funcs = { .restore = intel_fbdev_client_restore };
int main(int argc, char **argv) {
    struct drm_client_dev client = {0};
    struct intel_fbdev fbdev = {0};
    int ret;
    if (argc != 5) return 2;
    helper_ret = atoi(argv[2]);
    if (atoi(argv[3])) device.display.fbdev.fbdev = &fbdev;
    if (atoi(argv[4])) fbdev.vma = &fbdev;
#if MATEBOOK_DRM_CLIENT_RESTORE_HAS_FORCE
    ret = funcs.restore(&client, atoi(argv[1]));
#else
    ret = funcs.restore(&client);
#endif
    printf("%d %d %d %d %d\n", ret, observed_force, helper_calls, invalidations, switches);
    return 0;
}
'''


class FbdevCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="matebook-fbdev-check-")
        cls.variants = {}
        functions = restore_functions()
        for helper in (0, 1):
            for client in (0, 1):
                exe = Path(cls.temp.name) / f"restore-{helper}-{client}"
                source = exe.with_suffix(".c")
                source.write_text(PREFIX + functions + MAIN)
                subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                                f"-DMATEBOOK_DRM_FB_HELPER_RESTORE_HAS_FORCE={helper}",
                                f"-DMATEBOOK_DRM_CLIENT_RESTORE_HAS_FORCE={client}",
                                str(source), "-o", str(exe)], check=True)
                cls.variants[helper, client] = exe

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_variants(self, force, helper_ret, fbdev, vma, ret, calls, invalidations, switches):
        for (helper, client), exe in self.variants.items():
            with self.subTest(helper_force=helper, client_force=client):
                result = tuple(map(int, subprocess.check_output(
                    [str(exe), str(force), str(helper_ret), str(fbdev), str(vma)], text=True).split()))
                observed = (force if client else 0) if helper and calls else -1
                self.assertEqual(result, (ret, observed, calls, invalidations, switches))

    def test_forced_restore_is_forwarded_when_supported(self):
        self.check_variants(1, 0, 1, 1, 0, 1, 1, 1)

    def test_normal_restore_does_not_force(self):
        self.check_variants(0, 0, 1, 1, 0, 1, 1, 1)

    def test_helper_error_stops_restore(self):
        self.check_variants(1, -5, 1, 1, -5, 1, 0, 0)

    def test_missing_fbdev_does_not_call_helper(self):
        self.check_variants(1, 0, 0, 1, -22, 0, 0, 0)

    def test_missing_vma_does_not_call_helper(self):
        self.check_variants(1, 0, 1, 0, -12, 0, 0, 0)


if __name__ == "__main__":
    unittest.main()
