import SwiftUI
import MAMapKit

// MARK: - 高德地图导航视图
struct AMapNavigationView: UIViewRepresentable {
    let routeCoordinates: [CLLocationCoordinate2D]
    let currentLocation: CLLocationCoordinate2D?
    let currentHeading: Double
    let currentSegmentIndex: Int
    let isOffRoute: Bool
    
    func makeUIView(context: Context) -> MAMapView {
        let mapView = MAMapView()
        mapView.delegate = context.coordinator
        
        // 配置地图
        mapView.mapType = .standard
        mapView.zoomEnabled = true
        mapView.scrollEnabled = true
        mapView.rotateEnabled = true
        mapView.showsUserLocation = false  // 使用自定义标记
        mapView.showsCompass = true
        mapView.showsScale = true
        mapView.userTrackingMode = .followWithHeading
        
        return mapView
    }
    
    func updateUIView(_ mapView: MAMapView, context: Context) {
        // 清除旧的覆盖物
        mapView.removeOverlays(mapView.overlays)
        mapView.removeAnnotations(mapView.annotations)
        
        // 绘制完整路线（灰色）
        if !routeCoordinates.isEmpty {
            let fullPolyline = MAPolyline(coordinates: routeCoordinates, count: UInt(routeCoordinates.count))
            mapView.add(fullPolyline)
            
            // 调整地图视野以显示整条路线
            if let first = routeCoordinates.first {
                let lats = routeCoordinates.map { $0.latitude }
                let lons = routeCoordinates.map { $0.longitude }
                
                let minLat = lats.min() ?? 0
                let maxLat = lats.max() ?? 0
                let minLon = lons.min() ?? 0
                let maxLon = lons.max() ?? 0
                
                let region = MACoordinateRegion(
                    center: CLLocationCoordinate2D(
                        latitude: (minLat + maxLat) / 2,
                        longitude: (minLon + maxLon) / 2
                    ),
                    span: MACoordinateSpan(
                        latitudeDelta: (maxLat - minLat) * 1.3 + 0.01,
                        longitudeDelta: (maxLon - minLon) * 1.3 + 0.01
                    )
                )
                
                mapView.setRegion(region, animated: false)
            }
        }
        
        // 绘制已走过的路线（绿色）
        if currentSegmentIndex > 0 && currentSegmentIndex < routeCoordinates.count {
            let completedCoords = Array(routeCoordinates[0..<currentSegmentIndex])
            let completedPolyline = MAPolyline(coordinates: completedCoords, count: UInt(completedCoords.count))
            mapView.add(completedPolyline)
        }
        
        // 添加起点标记
        if let start = routeCoordinates.first {
            let annotation = MAPointAnnotation()
            annotation.coordinate = start
            annotation.title = "起点"
            mapView.addAnnotation(annotation)
        }
        
        // 添加终点标记
        if let end = routeCoordinates.last, routeCoordinates.count > 1 {
            let annotation = MAPointAnnotation()
            annotation.coordinate = end
            annotation.title = "终点"
            mapView.addAnnotation(annotation)
        }
        
        // 添加当前位置标记
        if let location = currentLocation {
            let annotation = MAUserLocationAnnotation()
            annotation.coordinate = location
            annotation.title = "当前位置"
            mapView.addAnnotation(annotation)
            
            // 跟随用户位置
            if !isOffRoute {
                mapView.setCenter(location, animated: true)
            }
        }
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }
    
    class Coordinator: NSObject, MAMapViewDelegate {
        func mapView(_ mapView: MAMapView!, rendererFor overlay: MAOverlay!) -> MAOverlayRenderer! {
            if let polyline = overlay as? MAPolyline {
                let renderer = MAPolylineRenderer(overlay: polyline)
                
                // 根据路线类型设置不同颜色
                if let title = polyline.title, title == "completed" {
                    renderer?.strokeColor = UIColor.systemGreen
                    renderer?.lineWidth = 5
                } else {
                    renderer?.strokeColor = UIColor.gray.withAlphaComponent(0.5)
                    renderer?.lineWidth = 3
                }
                
                return renderer
            }
            
            return nil
        }
        
        func mapView(_ mapView: MAMapView!, viewFor annotation: MAAnnotation!) -> MAAnnotationView! {
            // 处理用户位置标注
            if annotation is MAUserLocationAnnotation {
                let identifier = "UserLocation"
                
                var annotationView = mapView.dequeueReusableAnnotationView(withIdentifier: identifier)
                
                if annotationView == nil {
                    annotationView = MAAnnotationView(annotation: annotation, reuseIdentifier: identifier)
                } else {
                    annotationView?.annotation = annotation
                }
                
                // 创建方向箭头
                let config = UIImage.SymbolConfiguration(pointSize: 20, weight: .bold)
                let image = UIImage(systemName: "location.north.fill", withConfiguration: config)?
                    .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
                
                annotationView?.image = image
                annotationView?.centerOffset = .zero
                
                return annotationView
            }
            
            // 处理起点/终点标注
            if let title = annotation.title {
                let identifier = "RoutePoint"
                var annotationView = mapView.dequeueReusableAnnotationView(withIdentifier: identifier) as? MAPinAnnotationView
                
                if annotationView == nil {
                    annotationView = MAPinAnnotationView(annotation: annotation, reuseIdentifier: identifier)
                } else {
                    annotationView?.annotation = annotation
                }
                
                if title == "起点" {
                    annotationView?.pinColor = .green
                } else if title == "终点" {
                    annotationView?.pinColor = .red
                }
                
                annotationView?.canShowCallout = true
                
                return annotationView
            }
            
            return nil
        }
    }
}

// 自定义用户位置标注
class MAUserLocationAnnotation: MAPointAnnotation {
    
}
