# Experimental build only. Deliberately has no flashing target.
SDCC ?= sdcc
HOST_CC ?= cc
FLAGS = -mmcs51 --model-small --std-c99 --opt-code-size
BUILD = build
R2 = t7-stc8g-power-r2-idle
R3 = t7-stc8g-power-r3-stop

.PHONY: all check
all: check $(BUILD)/$(R3).hex $(BUILD)/$(R2).hex
	python3 check_image.py

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/controller.rel: controller.c controller.h | $(BUILD)
	$(SDCC) $(FLAGS) -c controller.c -o $@

$(BUILD)/main-r3.rel: main.c controller.h | $(BUILD)
	$(SDCC) $(FLAGS) -c main.c -o $@

$(BUILD)/main-r2.rel: main.c controller.h | $(BUILD)
	$(SDCC) $(FLAGS) -DT7_IDLE_STANDBY -c main.c -o $@

$(BUILD)/$(R3).ihx: $(BUILD)/main-r3.rel $(BUILD)/controller.rel
	$(SDCC) $(FLAGS) --code-size 8192 --iram-size 256 $^ -o $@

$(BUILD)/$(R2).ihx: $(BUILD)/main-r2.rel $(BUILD)/controller.rel
	$(SDCC) $(FLAGS) --code-size 8192 --iram-size 256 $^ -o $@

$(BUILD)/%.hex: $(BUILD)/%.ihx
	packihx $< > $@

$(BUILD)/test-controller: test_controller.c controller.c controller.h | $(BUILD)
	$(HOST_CC) -std=c99 -Wall -Wextra -Werror test_controller.c controller.c -o $@

check: $(BUILD)/test-controller
	./$(BUILD)/test-controller
	python3 test_standby.py
