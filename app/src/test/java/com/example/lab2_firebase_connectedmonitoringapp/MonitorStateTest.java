package com.example.lab2_firebase_connectedmonitoringapp;
import org.junit.Test;
import static org.junit.Assert.*;
public class MonitorStateTest {
    @Test public void alertRequiresModeAndStrictExceedance() {
        assertTrue(MonitorState.isHigh(31.0, 30.0, true));
        assertFalse(MonitorState.isHigh(30.0, 30.0, true));
        assertFalse(MonitorState.isHigh(29.0, 30.0, true));
        assertFalse(MonitorState.isHigh(40.0, 30.0, false));
        assertFalse(MonitorState.isHigh(null, 30.0, true));
        assertFalse(MonitorState.isHigh(40.0, null, true));
    }
    @Test public void rejectMalformedNumbers() {
        assertNull(MonitorState.number("35"));
        assertNull(MonitorState.number(null));
        assertNull(MonitorState.number(Double.NaN));
        assertNull(MonitorState.number(Double.POSITIVE_INFINITY));
        assertEquals(35.0, MonitorState.number(35L), 0);
    }
    @Test public void thresholdsAreBounded() {
        assertEquals(31, MonitorState.nextThreshold(30, 1), 0);
        assertEquals(29, MonitorState.nextThreshold(30, -1), 0);
        assertEquals(100, MonitorState.nextThreshold(100, 1), 0);
        assertEquals(-50, MonitorState.nextThreshold(-50, -1), 0);
    }
}
