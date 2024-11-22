# Bustime - public transport online

**Live Demo Available at:** [busti.me](https://busti.me/)

Bustime is a full-stack software solution built with Python/Django to process and visualize real-time public transport data. Designed to manage the complete lifecycle of transport tracking, Bustime collects GPS data, including direct communication with tracking devices via low-level protocols, ensuring precise, real-time positioning of vehicles. The platform includes route management, data processing, user rights administration, track history storage, arrival time prediction, and an open-source API for mobile applications. Additionally, Bustime supports the processing of GTFS and GTFS-RT data formats to enhance integration with other transit systems.

## Key Features

- **Real-Time GPS Data Collection:** Captures vehicle positions directly from trackers via low-level protocols, offering high accuracy.
- **Nearest Stop Detection and Direction Tracking:** Calculates the closest stop and tracks the vehicle’s direction to estimate accurate arrival times.
- **Route and Data Management:** Includes comprehensive tools for editing routes, adjusting timetables, and processing real-time data.
- **GTFS and GTFS-RT Integration:** Supports GTFS static and real-time feeds for extended compatibility with other transit platforms and services.
- **User Access Control:** Manages user permissions to provide secure access and customized functionality based on user roles.
- **Track History and Analytics:** Stores track history for in-depth analysis, enabling monitoring of vehicle performance and route efficiency.
- **API for Mobile Applications:** Provides a robust, open-source API for seamless mobile integration, giving end-users access to real-time data and features.
- **Advanced State Detection:** Identifies “sleeping” (inactive) and “zombie” (potentially malfunctioning) states to maintain optimal service reliability.

## Supported Transport Types

- Bus
- Trolleybus
- Tramway
- Inter-city Bus
- Shuttle Bus
- Ferry
- Train
- Metro

---

Bustime offers an all-in-one solution for managing, visualizing, and optimizing public transport services with flexible integration options and robust, real-time data handling capabilities.

#### License
Published under [MIT](LICENSE) license.
