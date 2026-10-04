# ShadowVault (FOGSAFE) - Hardware & Sensor Architecture

This document outlines the working principles and specific roles of each hardware component used in the ShadowVault FOGSAFE mining vehicle prototype. The system utilizes a multi-layered sensor approach to guarantee safety during severe monsoon conditions, dense fog, and low visibility.

## 1. Microcontrollers & Processing Units

### ESP32 (Edge Processing Node)
* **Function:** Acts as the primary data acquisition and edge-processing unit on each dumper.
* **Working:** The ESP32 continuously polls the entire sensor array at high frequencies. It performs local calculations (such as Time-To-Collision) to ensure extremely low-latency warnings. By processing data at the edge, the system doesn't rely entirely on the cloud, which is critical in remote mining zones with poor connectivity.

### Raspberry Pi (Central / Advanced Processing)
* **Function:** Handles higher-level computer vision algorithms and central data aggregation.
* **Working:** Processes the heavy visual data from the RGB cameras and thermal arrays. It translates the raw sensor data into the UI dashboard elements and handles the complex logic required for the centralized control room.

---

## 2. Environmental & Proximity Sensors

### MLX90640 (Thermal Imaging Camera)
* **Function:** Detects heat signatures of living beings (workers) and active machinery (other dumpers).
* **Working:** Unlike standard optical cameras that fail in thick fog or dust, this 32x24 pixel IR array detects the infrared radiation emitted by objects. It allows the system to "see" the heat of an engine or a person through dense atmospheric interference, alerting the driver long before the object is visibly clear.

### HLK-LD2450 (Radar Sensor)
* **Function:** Maps the distance, speed, and position of surrounding infrastructure and vehicles.
* **Working:** Emits millimeter-wave radio signals and measures the time it takes for the signals to bounce back from objects (Time of Flight). Because radio waves penetrate fog, heavy rain, and dust effortlessly, the radar serves as the primary failsafe for calculating exact distance and approach speeds of unseen obstacles.

### HC-SR04 (Ultrasonic Sensors)
* **Function:** Provides high-precision, near-field obstacle detection.
* **Working:** Emits high-frequency sound waves (ultrasound) and listens for the echo. This is primarily used for close-quarters maneuvering (like reversing or tight cornering in the pit) where radar might have blind spots. If a rock or berm is too close, the ultrasonic sensor triggers an immediate stop warning.

### RGB Camera (Visual Detection)
* **Function:** Standard optical object classification and lane detection.
* **Working:** Feeds real-time video to the computer vision algorithms on the Raspberry Pi. During clear weather or moderate visibility, it acts as the primary tool for identifying the exact type of vehicle ahead and reading environmental markers.

---

## 3. Telemetry & Atmospheric Sensors

### MPU6050 (Inertial Measurement Unit / IMU)
* **Function:** Monitors the physical orientation, tilt, and acceleration of the dumper.
* **Working:** Contains a 3-axis accelerometer and a 3-axis gyroscope. In an open-cast mine, dumpers navigate steep inclines and uneven terrain. The IMU detects dangerous tilt angles (rollover risk) or sudden harsh braking, immediately sending alerts to the control room.

### GPS / GNSS Module
* **Function:** Provides continuous, absolute global positioning.
* **Working:** Connects to satellite networks to pinpoint the exact coordinates of the truck on the terraced mine map. If a truck breaks down in dense fog, the GPS coordinates are instantly broadcast to all other trucks, warning them of a stationary hazard at that exact location.

### DHT11 / DHT22 (Temperature & Humidity Sensor)
* **Function:** Monitors localized atmospheric conditions.
* **Working:** Measures the ambient moisture and temperature in the air. This data is used to automatically predict and verify the presence of fog. If humidity spikes while temperature drops, the system can proactively switch the UI into "Low-Visibility Mode" even before the cameras are fully obscured.

---

## 4. V2X Communication

### nRF24L01 (V2V / V2I Transceivers)
* **Function:** Establishes a localized, offline radio network between vehicles (Vehicle-to-Vehicle) and infrastructure (Vehicle-to-Infrastructure).
* **Working:** Operates on the 2.4GHz ISM band. It allows trucks to directly ping each other with their GPS coordinates and speed without needing an internet connection or cell tower. This is how the system achieves "Blind Curve Detection"—a truck can "hear" another truck's nRF24L01 signal coming around a corner long before any camera or radar can see it.

