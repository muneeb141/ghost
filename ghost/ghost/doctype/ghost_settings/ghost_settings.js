// Copyright (c) 2026, Muneeb Mohammed and contributors
// For license information, please see license.txt

frappe.ui.form.on("Ghost Settings", {
    /**
     * Called on form load and refresh.
     * Enforces that sandbox_otp is always read-only and
     * pre-fills it if the field is empty.
     */
    refresh(frm) {
        frm.set_df_property("sandbox_otp", "read_only", 1);

        if (frm.doc.sandbox_mode && !frm.doc.sandbox_otp) {
            frm.set_value("sandbox_otp", "000141");
        }
    },

    /**
     * Reacts to the sandbox_mode checkbox toggle.
     * When enabled → auto-fill the fixed OTP.
     * When disabled → clear the field (optional, keeps UI clean).
     */
    sandbox_mode(frm) {
        if (frm.doc.sandbox_mode) {
            frm.set_value("sandbox_otp", "000141");
            frappe.show_alert({
                message: __("Sandbox Mode enabled. Use OTP <strong>000141</strong> for authentication."),
                indicator: "orange",
            }, 5);
        } else {
            frm.set_value("sandbox_otp", "");
        }
    },
});
