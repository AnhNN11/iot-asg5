package com.example.lab2_firebase_connectedmonitoringapp;

import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import com.google.android.material.switchmaterial.SwitchMaterial;
import com.google.firebase.database.*;
import java.text.DateFormat;
import java.util.Date;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {
    private static final String TAG = "FirebaseMonitor";
    private DatabaseReference latest, connection;
    private ValueEventListener dataListener, connectionListener;
    private TextView temperatureView, humidityView, thresholdView, statusView, alertView, timeView;
    private SwitchMaterial modeSwitch;
    private Button increase, decrease;
    private Double temperature, humidity, threshold;
    private boolean mode, rendering, wasHigh, connected, writePending, dataReady;
    private MediaPlayer player;
    private boolean localEmulator;
    private String readError;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_main);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.root), (v, insets) -> {
            androidx.core.graphics.Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            return insets;
        });
        temperatureView = findViewById(R.id.temperature);
        humidityView = findViewById(R.id.humidity);
        thresholdView = findViewById(R.id.threshold);
        statusView = findViewById(R.id.connection);
        alertView = findViewById(R.id.alert);
        timeView = findViewById(R.id.timestamp);
        modeSwitch = findViewById(R.id.mode);
        increase = findViewById(R.id.increase);
        decrease = findViewById(R.id.decrease);
        localEmulator = BuildConfig.DEBUG && getIntent().getBooleanExtra("localEmulator", false);
        FirebaseDatabase database;
        if (localEmulator) {
            com.google.firebase.FirebaseApp app;
            try { app = com.google.firebase.FirebaseApp.getInstance("local-exercise3"); }
            catch (IllegalStateException missing) {
                app = com.google.firebase.FirebaseApp.initializeApp(this,
                        new com.google.firebase.FirebaseOptions.Builder()
                                .setApplicationId(getString(R.string.google_app_id))
                                .setProjectId("demo-exercise3")
                                .setDatabaseUrl("https://demo-exercise3-default-rtdb.firebaseio.com").build(), "local-exercise3");
                FirebaseDatabase.getInstance(app).useEmulator("127.0.0.1", 9000);
            }
            database = FirebaseDatabase.getInstance(app);
            ((TextView)findViewById(R.id.source)).setText("LOCAL FIREBASE EMULATOR • Config / Latest");
            Log.i(TAG, "TEST ENVIRONMENT: Firebase Emulator 127.0.0.1:9000 via adb reverse, demo-exercise3");
        } else database = FirebaseDatabase.getInstance(getString(R.string.database_url));
        latest = database.getReference("Config/Latest");
        connection = database.getReference(".info/connected");
        increase.setOnClickListener(v -> changeThreshold(1));
        decrease.setOnClickListener(v -> changeThreshold(-1));
        modeSwitch.setOnCheckedChangeListener((button, checked) -> {
            if (rendering) return;
            writePending = true;
            render();
            latest.child("Mode").setValue(checked, (error, ref) -> {
                writePending = false;
                if (error != null) showError("Mode", error);
                else Log.d(TAG, "Mode committed: " + checked);
                render();
            });
        });
        render();
    }

    @Override protected void onStart() { super.onStart(); setupListeners(); }

    /** One snapshot keeps temperature, humidity, threshold and mode consistent. */
    private void setupListeners() {
        dataListener = new ValueEventListener() {
            @Override public void onDataChange(DataSnapshot snapshot) {
                readError = null;
                temperature = MonitorState.number(snapshot.child("Temperature").getValue());
                if (temperature != null && (temperature < -50 || temperature > 150)) temperature = null;
                humidity = MonitorState.number(snapshot.child("Humidity").getValue());
                if (humidity != null && (humidity < 0 || humidity > 100)) humidity = null;
                threshold = MonitorState.number(snapshot.child("Threshold").getValue());
                Object rawMode = snapshot.child("Mode").getValue();
                mode = Boolean.TRUE.equals(rawMode) || (rawMode instanceof Number && ((Number) rawMode).intValue() == 1);
                dataReady = temperature != null && humidity != null && threshold != null
                        && threshold >= -50 && threshold <= 100
                        && (rawMode instanceof Boolean || (rawMode instanceof Number
                        && (((Number) rawMode).doubleValue() == 0 || ((Number) rawMode).doubleValue() == 1)));
                Object timestamp = snapshot.child("Timestamp").getValue();
                if (timestamp instanceof Number) {
                    timeView.setText("Updated: " + DateFormat.getDateTimeInstance().format(new Date(((Number) timestamp).longValue())));
                } else timeView.setText("Timestamp: " + (timestamp == null ? "not supplied" : timestamp));
                Log.d(TAG, "Temperature=" + temperature + ", Humidity=" + humidity
                        + ", Threshold=" + threshold + ", Mode=" + mode + ", Timestamp=" + timestamp);
                boolean high = dataReady && MonitorState.isHigh(temperature, threshold, mode);
                if (high && !wasHigh && connected) notifyHighTemperature();
                wasHigh = high && connected;
                render();
            }
            @Override public void onCancelled(DatabaseError error) {
                dataReady = false;
                readError = error.getMessage();
                showError("Read Config/Latest", error);
                render();
            }
        };
        connectionListener = new ValueEventListener() {
            @Override public void onDataChange(DataSnapshot snapshot) {
                connected = Boolean.TRUE.equals(snapshot.getValue(Boolean.class));
                Log.d(TAG, "Connected=" + connected);
                if (!connected) wasHigh = false;
                else if (dataReady && MonitorState.isHigh(temperature, threshold, mode) && !wasHigh) {
                    notifyHighTemperature(); wasHigh = true;
                }
                render();
            }
            @Override public void onCancelled(DatabaseError error) { connected = false; render(); }
        };
        latest.addValueEventListener(dataListener);
        connection.addValueEventListener(connectionListener);
    }

    private void changeThreshold(int delta) {
        writePending = true; render();
        latest.child("Threshold").runTransaction(new Transaction.Handler() {
            @Override public Transaction.Result doTransaction(MutableData current) {
                Double value = MonitorState.number(current.getValue());
                if (value == null || value < -50 || value > 100) return Transaction.abort();
                current.setValue(MonitorState.nextThreshold(value, delta));
                return Transaction.success(current);
            }
            @Override public void onComplete(DatabaseError error, boolean committed, DataSnapshot snapshot) {
                writePending = false;
                if (error != null) showError("Threshold", error);
                else if (!committed) Toast.makeText(MainActivity.this, "Invalid or missing threshold", Toast.LENGTH_SHORT).show();
                else Log.d(TAG, "Threshold committed: " + snapshot.getValue());
                render();
            }
        }, false);
    }

    private void render() {
        temperatureView.setText(format(temperature, "°C"));
        humidityView.setText(format(humidity, "%"));
        thresholdView.setText(format(threshold, "°C"));
        rendering = true; modeSwitch.setChecked(mode); rendering = false;
        boolean ready = connected && dataReady && !writePending;
        increase.setEnabled(ready && threshold < 100);
        decrease.setEnabled(ready && threshold > -50);
        modeSwitch.setEnabled(ready);
        statusView.setText(!connected ? "Offline • waiting for Firebase" : writePending ? "Saving to Firebase…"
                : dataReady ? localEmulator ? "Live • LOCAL Firebase Emulator" : "Live • Firebase connected" : "Connected • missing or invalid data");
        if (readError != null) statusView.setText("Database error: " + readError);
        boolean high = dataReady && MonitorState.isHigh(temperature, threshold, mode);
        alertView.setText(!dataReady ? "Waiting for valid sensor data" : !connected ? "Offline • values may be stale"
                : !mode ? "Alerts paused • mode is OFF" : high ? "HIGH TEMPERATURE • threshold exceeded" : "Normal • temperature within threshold");
        alertView.setTextColor(high ? 0xFFB3261E : 0xFF12695F);
    }
    private String format(Double number, String unit) {
        return number == null ? "— " + unit : String.format(Locale.US, "%.1f %s", number, unit);
    }
    private void notifyHighTemperature() {
        Toast.makeText(this, "Warning: Temperature exceeds threshold!", Toast.LENGTH_LONG).show();
        Log.w(TAG, "ALERT: Warning: Temperature exceeds threshold!");
        releasePlayer();
        player = MediaPlayer.create(this, R.raw.alert_tone,
                new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_NOTIFICATION_EVENT)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build(), 0);
        if (player != null) {
            player.setOnCompletionListener(mp -> { mp.release(); if (player == mp) player = null; });
            player.setOnErrorListener((mp, what, extra) -> { Log.e(TAG, "Sound error=" + what); mp.release(); player = null; return true; });
            player.start();
            Log.d(TAG, "Notification sound started");
        }
    }
    private void showError(String operation, DatabaseError error) {
        Log.e(TAG, operation + ": " + error.getMessage());
        Toast.makeText(this, operation + ": " + error.getMessage(), Toast.LENGTH_LONG).show();
    }
    private void releasePlayer() {
        if (player != null) { try { player.release(); } catch (RuntimeException ignored) {} player = null; }
    }
    @Override protected void onStop() {
        if (dataListener != null) latest.removeEventListener(dataListener);
        if (connectionListener != null) connection.removeEventListener(connectionListener);
        connected = false; wasHigh = false; releasePlayer();
        super.onStop();
    }
}
