package com.juancavr6.regibot;

import android.content.Context;
import android.graphics.Bitmap;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import com.juancavr6.regibot.ml.ModelHandler;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

/** Verifies that packaged assets and JNI libraries actually run on the device ABI. */
@RunWith(AndroidJUnit4.class)
public class NativeModelsTest {
    @Test
    public void packagedModelsCanRunInference() {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        Bitmap frame = Bitmap.createBitmap(256, 256, Bitmap.Config.ARGB_8888);
        try {
            for (String name : new String[]{"model_detector_map_v2.tflite",
                    "model_detector_encounter.tflite", "model_detector_clickable_v2.tflite"}) {
                try (ModelHandler.Detector detector = ModelHandler.buildDetector(context, name, 3)) {
                    assertNotNull("Could not load " + name, detector);
                    detector.detect(frame);
                    assertNotNull(detector.getDetectionList());
                }
            }
            try (ModelHandler.Classifier classifier = ModelHandler.buildClassifier(
                    context, "model_classifier_screen_v5.tflite", 3)) {
                assertNotNull("Could not load classifier", classifier);
                classifier.classify(frame);
                assertFalse(classifier.getClassificationList().isEmpty());
            }
            try (ModelHandler.Predictor predictor = ModelHandler.buildPredictor(context, "predictor.tflite")) {
                predictor.predict(new float[]{0.5f, 0.5f, 0.1f, 0.1f});
                assertTrue(Float.isFinite(predictor.getDeltaY()));
                assertTrue(Float.isFinite(predictor.getDuration()));
            }
        } finally {
            frame.recycle();
        }
    }
}
