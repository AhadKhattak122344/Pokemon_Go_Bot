package com.juancavr6.regibot.services;

import android.accessibilityservice.AccessibilityService;

import android.content.Intent;
import android.graphics.Insets;
import android.graphics.Rect;

import android.os.Handler;
import android.util.Log;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.view.WindowMetrics;
import android.view.accessibility.AccessibilityEvent;

import com.juancavr6.regibot.executor.ActionLooper;

import java.util.concurrent.Executor;

public class ActionService extends AccessibilityService {

    public static ActionService instance = null;

    private final String TAG = "ACTION_SERVICE";

    public ActionLooper actionLoop;
    public Thread actionLoopThread;

    //Display metrics
    public int displayWidth;
    public int displayHeight;



    //Main executor instance for tasks launching
    public Executor mainExecutor;
    public Handler mainHandler;


    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        mainExecutor = this.getMainExecutor();
        mainHandler = new Handler(getMainLooper());
    }
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        handleAction(intent == null ? null : intent.getStringExtra("action"));
        return START_NOT_STICKY;
    }
    private void getScreenSize() {
        try {
            WindowManager windowManager = getSystemService(WindowManager.class);
            WindowMetrics windowMetrics = windowManager.getCurrentWindowMetrics();

            WindowInsets windowInsets = windowMetrics.getWindowInsets();
            Insets insets = windowInsets.getInsetsIgnoringVisibility(WindowInsets.Type.systemBars());

            Rect bounds = windowMetrics.getBounds();

            displayWidth = bounds.width() - insets.left - insets.right;
            displayHeight = bounds.height() - insets.top - insets.bottom;
        } catch (Exception e) {
            android.util.DisplayMetrics displayMetrics = getResources().getDisplayMetrics();
            displayWidth = displayMetrics.widthPixels;
            displayHeight = displayMetrics.heightPixels;
        }
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {}
    @Override
    public void onInterrupt() { handleAction("pause"); }

    @Override
    public void onDestroy() {
        handleAction("destroy");
        mainHandler.removeCallbacksAndMessages(null);
        instance = null;
        super.onDestroy();
        Log.d(TAG,"onDestroy(): stopping self");
    }

    public void handleAction(String action) {
        Log.d(TAG, "handleAction(): Action received: " + action);
        if (action == null) return;

        if (action.equals("play")) {
            getScreenSize(); // Initialize width, height and dpi

            if (actionLoopThread != null && actionLoopThread.isAlive()) return;
            actionLoop = new ActionLooper(this);
            actionLoopThread = new Thread(actionLoop, "regibot-actions");
            actionLoopThread.start();
        } else if (action.equals("pause")) { // Put loop thread on pause, not service
            Log.d(TAG, "handleAction(): Action Pause");
            if (actionLoop != null) {
                actionLoop.pause();
            }
        } else if (action.equals("resume")) {
            Log.d(TAG, "handleAction(): Action Resume");
            if (actionLoop != null) {
                actionLoop.resume();
            }
        } else if (action.equals("destroy")) {
            Log.d(TAG, "handleAction(): Action Destroy");
            if (actionLoop != null) {
                actionLoop.stop();
                if (actionLoopThread != null) actionLoopThread.interrupt();
                mainHandler.removeCallbacksAndMessages(null);
            }
        }
    }

}