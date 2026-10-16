// SPDX-License-Identifier: MIT
#include <linux/build_bug.h>
#include <drm/drm_client.h>

#if MATEBOOK_TEST_FORCE
typedef int (*restore_fn)(struct drm_client_dev *, bool);
#else
typedef int (*restore_fn)(struct drm_client_dev *);
#endif

static_assert(__same_type(typeof(((struct drm_client_funcs *)0)->restore),
			 restore_fn));
