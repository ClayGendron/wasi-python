"""Spec 057's mutations of the real release.yml: each must be named by the judge's scans."""
import sys
sys.path.insert(0, "tests")
from harness import scan

t = open(".github/workflows/release.yml").read()
loop = '"$ARM64_SUMS_ID" "$ARM64_WHEEL_ID" "$X86_64_SUMS_ID" "$X86_64_WHEEL_ID"'
arm = "artifact-ids: ${{ needs.rebuild-linux-arm64.outputs.sums-id }}"
pub = t.index("  publish:")
check = "      - name: These are the bytes the build job made\n"
g0 = t.index("      - name: The build job handed on an artifact id")
GUARD = t[g0 : t.index("      - uses: actions/download-artifact@", g0)]
muts = {
    "M1 rebuild guard binds X86_64_WHEEL_ID, loop drops it": t.replace(loop, loop.replace(' "$X86_64_WHEEL_ID"', "")),
    "M2 continue-on-error on the rebuild guard": t.replace("      - name: The rebuild jobs handed on artifact ids\n", "      - name: The rebuild jobs handed on artifact ids\n        continue-on-error: true\n"),
    "M5 x86_64 sums-id into the arm64 folder": t.replace(arm, arm.replace("arm64", "x86-64")),
    "M6 continue-on-error on publish's check": t[:pub] + t[pub:].replace(check, check + "        continue-on-error: true\n", 1),
    "F1 the guard removed from attest": t[: t.index("  attest:")] + t[t.index("  attest:"):].replace(GUARD, "", 1),
    "F4 release-assets by name (pypi)": t[: t.index("  pypi:")] + t[t.index("  pypi:"):].replace("artifact-ids: ${{ needs.build.outputs.assets-id }}", "name: release-assets", 1),
    "the old matrix rebuild (main's workflow)": open(sys.argv[1]).read(),
}
print("real workflow:", "binding", scan.release_binding_errors(t), "gate", scan.rebuild_gate_errors(t), "attest", scan.release_attestation_errors(t), "pins", scan.action_pin_errors(t))
for name, text in muts.items():
    assert text != t or name.startswith("the old"), name
    b, g = scan.release_binding_errors(text), scan.rebuild_gate_errors(text)
    print(f"{name}: caught={bool(b or g)} | " + "; ".join((b + g)[:3]))
