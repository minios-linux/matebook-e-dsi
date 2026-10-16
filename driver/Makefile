# DKMS 驱动这个包装 Makefile; 真正的模块在 drivers/gpu/drm/i915 下。
KDIR ?= /lib/modules/$(shell uname -r)/build
I    := drivers/gpu/drm/i915

all:
	+$(SHELL) $(CURDIR)/compat/configure.sh "$(KDIR)" "$(CURDIR)/$(I)/matebook_kernel_compat.h" "$(MAKE)"
	$(MAKE) -C $(KDIR) M=$(CURDIR)/$(I) modules

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR)/$(I) clean
	$(RM) $(CURDIR)/$(I)/matebook_kernel_compat.h

.PHONY: all clean
