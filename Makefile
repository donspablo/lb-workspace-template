DIR := $(abspath $(dir $(realpath $(lastword $(MAKEFILE_LIST)))))

ifeq (${DIR}, ${CURDIR})
  $(error do not run make inside ${DIR})
endif

# default target
all:

# clone projects, write project settings .mk file and source it
# also defines build target
include $(shell "$(DIR)/setup-make.py" $(MAKECMDGOALS))

# main targets
all: build

CMD = true
for-each:
	@for p in $(REPOS) ; do if [[ -d $$p && ! " $(EXCLUDE) " == *" $$p "*  ]] ; then ( cd $$p && pwd && $(CMD) ) ; fi ; done

CONTRIB_DEPS += $(CONTRIB_PATH)/bin/distcc
CONTRIB_DEPS += $(CONTRIB_PATH)/bin/ninjatracing $(CONTRIB_PATH)/bin/post_build_ninja_summary.py
contrib: $(CONTRIB_DEPS)
$(CONTRIB_PATH)/bin/%: $(DIR)/install-%.sh
	@"${DIR}/build-env" bash "$<"
$(CONTRIB_PATH)/bin/ninjatracing $(CONTRIB_PATH)/bin/post_build_ninja_summary.py: $(DIR)/install-tools.sh
	@"${DIR}/build-env" bash "$<"

clean: $(patsubst %,%-clean,$(PROJECTS))
purge: $(patsubst %,%/purge,$(PROJECTS))

help:
	@for t in $(ALL_TARGETS) ; do echo .. $$t ; done

# public targets: main targets
ALL_TARGETS = all build clean purge contrib update

# ----------------------
# implementation details
# ----------------------

# public targets: project targets
ALL_TARGETS += $(foreach p,$(PROJECTS),$(p) $(p)/ $(p)-clean fast/$(p) fast/$(p)-clean)

define PROJECT_settings
# generic build target
$(1)/%: $$($(1)_DEPS) fast/$(1)/% ;
fast/$(1)/%: $(CONTRIB_DEPS)
	@$(DIR)/build-env $(DIR)/make.sh $(1) $$*
# check kerberos token when running tests
fast/$(1)/test: $(CONTRIB_DEPS)
	@$(DIR)/build-env --check-kerberos $(DIR)/make.sh $(1) test
# special checkout targets (noop here, as checkout is done in setup-make.py)
fast/$(1)/checkout: ;@# noop
$(1)/checkout: fast/$(1)/checkout ;
# exception for purge and clean: always do fast/Project/purge or clean
$(1)/purge: fast/$(1)/purge ;
fast/$(1)/purge:
	$(RM) -r $(1)/build.$(BINARY_TAG) $(1)/InstallArea/$(BINARY_TAG)
	find $(1) "(" -name "InstallArea" -prune -o -name "*.pyc" ")" -a -type f -exec $(RM) -v \{} \;
$(1)/clean: fast/$(1)/clean ;
# build... delegate to generic target
$(1): $(1)/install
$(1)/: $(1)/install
fast/$(1): fast/$(1)/install
# clean
$(1)-clean: $(patsubst %,%-clean,$($(1)_INV_DEPS))
	$$(MAKE) fast/$(1)-clean
fast/$(1)-clean:
	@test -d $(1)/build.$(BINARY_TAG) && $$(MAKE) $(1)/clean || true
	$(RM) -r $(1)/InstallArea/$(BINARY_TAG)
endef
$(foreach proj,$(PROJECTS),$(eval $(call PROJECT_settings,$(proj))))

# stack.code-workspace is always remade by setup-make.py, so this is just
# to avoid the message "Nothing to be done for `stack.code-workspace'"
stack.code-workspace: ;@# noop
update: ;@# noop

.PHONY: $(ALL_TARGETS) stack.code-workspace

# ignore -j flag and run serially
.NOTPARALLEL:

# debugging
# print-%  : ; @echo $* = $($*)
