package com.example.lab2_firebase_connectedmonitoringapp;

/** Pure validation and alert policy, shared by UI and tests. */
public final class MonitorState {
    private MonitorState() {}
    public static Double number(Object value) {
        if (!(value instanceof Number)) return null;
        double n = ((Number) value).doubleValue();
        return Double.isFinite(n) ? n : null;
    }
    public static boolean isHigh(Double temperature, Double threshold, boolean mode) {
        return mode && temperature != null && threshold != null && temperature > threshold;
    }
    public static double nextThreshold(double current, int delta) {
        return Math.max(-50, Math.min(100, current + delta));
    }
}
