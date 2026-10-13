"""Exercise the actual DSI PHY/header functions with a minimal MMIO mock.

This checks register values, not hardware timing or display acceptance.
MATEBOOK_REFERENCE_TREE optionally supplies the patched Linux reference for
an additional comparison of the same production functions.
"""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISPLAY = ROOT / "driver/drivers/gpu/drm/i915/display"


def extract_function(text, name):
    match = re.search(r"static (?:void|int) " + name + r"\([^;]*?\)\n\{", text)
    if match is None:
        raise AssertionError("missing function: " + name)
    start = match.start()
    pos = match.end()
    depth = 1
    while depth:
        depth += (text[pos] == "{") - (text[pos] == "}")
        pos += 1
    return text[start:pos]


def compile_functions(display, destination):
    text = (display / "icl_dsi.c").read_text()
    header = (display / "icl_dsi_regs.h").read_text()
    names = {
        "CLK_PREPARE_OVERRIDE", "CLK_PREPARE", "CLK_ZERO_OVERRIDE", "CLK_ZERO",
        "CLK_PRE_OVERRIDE", "CLK_PRE", "CLK_TRAIL_OVERRIDE", "HS_PREPARE_OVERRIDE",
        "HS_PREPARE", "HS_ZERO_OVERRIDE", "HS_ZERO", "HS_EXIT_OVERRIDE", "HS_EXIT",
        "HS_TRAIL_OVERRIDE", "PAYLOAD_PRESENT", "LP_DATA_TRANSFER", "VBLANK_FENCE",
        "PIPELINE_FLUSH", "PARAM_WC_MASK", "VC_MASK", "VC_SHIFT", "DT_MASK", "DT_SHIFT",
        "PARAM_WC_LOWER_SHIFT", "PARAM_WC_UPPER_SHIFT",
    }
    macros = []
    for line in header.splitlines():
        match = re.match(r"#define\s+(\w+)", line)
        if match and match[1] in names:
            macros.append(line)
    prefix = r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint32_t u32;
typedef uint8_t u8;
#define DIV_ROUND_UP(n, d) (((n) + (d) - 1) / (d))
#define min(a, b) ((a) < (b) ? (a) : (b))
#define DSI_CMD_TXHDR(tc) (tc)
enum transcoder { TRANSCODER_DSI_0, TRANSCODER_DSI_1 };
struct mipi_config { u32 tclk_prepare, tclk_prepare_clkzero, tclk_pre;
                     u32 ths_prepare, ths_prepare_hszero, ths_exit; };
struct intel_connector { struct { struct { struct { struct mipi_config *config;
                                      } dsi; } vbt; } panel; };
struct intel_encoder { int unused; };
struct intel_dsi { struct intel_encoder base; struct intel_connector *attached_connector;
                   u32 dphy_reg, dphy_data_lane_reg, tlpx; };
struct intel_dsi_host { struct intel_dsi *intel_dsi; int port; };
struct mipi_dsi_packet { const u8 *payload; u8 header[3]; };
struct intel_display { u32 value; bool credits; };
static struct intel_display mock;
static u32 intel_dsi_tlpx_ns(struct intel_dsi *dsi) { return dsi->tlpx; }
static void intel_dsi_log_params(struct intel_dsi *dsi) { (void)dsi; }
static struct intel_display *to_intel_display(struct intel_encoder *encoder)
{ (void)encoder; return &mock; }
static enum transcoder dsi_port_to_transcoder(int port) { return port; }
static bool wait_for_header_credits(struct intel_display *display, enum transcoder tc, int n)
{ (void)tc; (void)n; return display->credits; }
static u32 intel_de_read(struct intel_display *display, int reg)
{ (void)reg; return display->value; }
static void intel_de_write(struct intel_display *display, int reg, u32 value)
{ (void)reg; display->value = value; }
'''
    main = r'''
int main(int argc, char **argv) {
    struct mipi_config cfg = {0};
    struct intel_connector connector = {0};
    struct intel_dsi dsi = {0};
    connector.panel.vbt.dsi.config = &cfg;
    dsi.attached_connector = &connector;
    if (argc == 8) {
        dsi.tlpx = strtoul(argv[1], NULL, 0);
        cfg.tclk_prepare = strtoul(argv[2], NULL, 0);
        cfg.tclk_prepare_clkzero = strtoul(argv[3], NULL, 0);
        cfg.tclk_pre = strtoul(argv[4], NULL, 0);
        cfg.ths_prepare = strtoul(argv[5], NULL, 0);
        cfg.ths_prepare_hszero = strtoul(argv[6], NULL, 0);
        cfg.ths_exit = strtoul(argv[7], NULL, 0);
        icl_dphy_param_init(&dsi);
        printf("%u %u\n", dsi.dphy_reg, dsi.dphy_data_lane_reg);
    } else if (argc == 5) {
        struct intel_dsi_host host = { .intel_dsi = &dsi };
        struct mipi_dsi_packet packet = { .header = {0x39, 0x80, 0x00} };
        mock.value = strtoul(argv[1], NULL, 0);
        mock.credits = strtoul(argv[4], NULL, 0);
        packet.payload = strtoul(argv[3], NULL, 0) ? (const u8 *)"x" : NULL;
        int ret = dsi_send_pkt_hdr(&host, &packet, strtoul(argv[2], NULL, 0));
        printf("%d %u\n", ret, mock.value);
    } else {
        return 2;
    }
    return 0;
}
'''
    source = destination.with_suffix(".c")
    source.write_text(prefix + "\n".join(macros) + "\n" +
                      extract_function(text, "icl_dphy_param_init") + "\n" +
                      extract_function(text, "dsi_send_pkt_hdr") + "\n" + main)
    subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", str(source),
                    "-o", str(destination)], check=True)


def compile_vbt_layout(destination):
    text = (DISPLAY / "intel_bios.h").read_text()
    start = text.index("struct mipi_config {")
    pos = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[pos] == "{") - (text[pos] == "}")
        pos += 1
    declaration = text[start:text.index(";", pos) + 1]
    source = destination.with_suffix(".c")
    source.write_text("#include <stdint.h>\n#include <stddef.h>\n#include <stdio.h>\n"
                      "typedef uint32_t u32; typedef uint16_t u16; typedef uint8_t u8;\n"
                      "#define __packed __attribute__((packed))\n" + declaration + r'''
_Static_assert(sizeof(struct mipi_config) == 122, "VBT config size changed");
_Static_assert(offsetof(struct mipi_config, hs_tx_timeout) == 26, "VBT offsets changed");
int main(void) {
    struct mipi_config cfg = {0};
    ((unsigned char *)&cfg)[24] = 0x18;
    printf("%u %u %u %u %u\n", cfg.blanking_packets_during_bllp,
           cfg.lp_clock_during_lpm, cfg.dphy_param_valid,
           cfg.eot_pkt_disabled, cfg.enable_clk_stop);
    return 0;
}
''')
    subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", str(source),
                    "-o", str(destination)], check=True)


class DsiBaseFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="matebook-dsi-check-")
        cls.exe = Path(cls.temp.name) / "ported"
        compile_functions(DISPLAY, cls.exe)
        cls.layout = Path(cls.temp.name) / "layout"
        compile_vbt_layout(cls.layout)
        cls.reference = None
        if os.environ.get("MATEBOOK_REFERENCE_TREE"):
            cls.reference = Path(cls.temp.name) / "reference"
            compile_functions(Path(os.environ["MATEBOOK_REFERENCE_TREE"]) /
                              "drivers/gpu/drm/i915/display", cls.reference)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_function(self, *args):
        command = [str(self.exe), *map(str, args)]
        result = subprocess.check_output(command, text=True).strip()
        if self.reference:
            reference = subprocess.check_output([str(self.reference), *map(str, args)], text=True).strip()
            self.assertEqual(result, reference)
        return tuple(map(int, result.split()))

    def test_matebook_vbt_phy_values(self):
        self.assertEqual(self.run_function(50, 50, 310, 8, 50, 200, 110),
                         (0xc8690000, 0x84830083))

    def test_vbt_reserved_bits_keep_binary_layout(self):
        self.assertEqual(subprocess.check_output([str(self.layout)], text=True).strip(), "1 1 0 0 0")

    def test_trail_is_left_to_hardware(self):
        for tlpx in (50, 100, 200):
            clock, data = self.run_function(tlpx, 50, 310, 8, 50, 200, 110)
            self.assertEqual(clock & (1 << 7), 0)
            self.assertEqual(data & (1 << 15), 0)

    def test_clock_and_data_prepare_are_independent(self):
        clock, data = self.run_function(50, 25, 100, 8, 75, 250, 110)
        self.assertEqual((clock >> 28) & 7, 2)
        self.assertEqual((data >> 24) & 7, 6)

    def test_phy_field_limits(self):
        clock, data = self.run_function(50, 250, 2000, 255, 200, 2000, 1000)
        self.assertEqual((clock >> 28) & 7, 7)
        self.assertEqual((clock >> 20) & 15, 15)
        self.assertEqual((clock >> 16) & 3, 3)
        self.assertEqual((data >> 24) & 7, 7)
        self.assertEqual((data >> 16) & 15, 15)
        self.assertEqual(data & 7, 7)

    def test_lp_packet_clears_stale_flush_and_fence(self):
        ret, value = self.run_function(0xffffffff, 1, 1, 1)
        self.assertEqual(ret, 0)
        self.assertEqual(value & 0xf0000000, 0xc0000000)

    def test_hs_packet_flushes_without_lp_or_fence(self):
        ret, value = self.run_function(0xffffffff, 0, 0, 1)
        self.assertEqual(ret, 0)
        self.assertEqual(value & 0xf0000000, 0x10000000)

    def test_packet_is_not_written_without_credit(self):
        self.assertEqual(self.run_function(0x12345678, 0, 1, 0), (-16, 0x12345678))


if __name__ == "__main__":
    unittest.main()
