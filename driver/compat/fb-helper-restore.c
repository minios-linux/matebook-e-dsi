// SPDX-License-Identifier: MIT
#include <linux/build_bug.h>
#include <drm/drm_fb_helper.h>

#if MATEBOOK_TEST_FORCE
typedef int (*restore_fn)(struct drm_fb_helper *, bool);
#else
typedef int (*restore_fn)(struct drm_fb_helper *);
#endif

static_assert(__same_type(typeof(&drm_fb_helper_restore_fbdev_mode_unlocked),
			 restore_fn));
