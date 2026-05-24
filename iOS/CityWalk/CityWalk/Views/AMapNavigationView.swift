import SwiftUI
import MAMapKit

// MARK: - 高德地图导航视图
struct AMapNavigationView: UIViewRepresentable {
    let routeCoordinates: [CLLocationCoordinate2D]
    let currentLocation: CLLocationCoordinate2D?
    let currentHeading: Double
    let currentSegmentIndex: Int
    let isOffRoute: Bool
    var selectedLayer: MapLayerMode = .standard
    
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
        
        // 初始绘制路线
        context.coordinator.updateOverlays(mapView: mapView, routeCoordinates: routeCoordinates, currentSegmentIndex: currentSegmentIndex)
        
        return mapView
    }
    
    func updateUIView(_ mapView: MAMapView, context: Context) {
        let coordinator = context.coordinator
        
        // 只在路线数据真正变化时才重建覆盖物
        let needsFullUpdate = coordinator.lastRouteCoordinatesCount != routeCoordinates.count
        let needsProgressUpdate = coordinator.lastSegmentIndex != currentSegmentIndex
        let needsLocationUpdate = coordinator.lastLocation != currentLocation
        let needsLayerUpdate = coordinator.lastSelectedLayer != selectedLayer
        
        if needsFullUpdate {
            coordinator.updateOverlays(mapView: mapView, routeCoordinates: routeCoordinates, currentSegmentIndex: currentSegmentIndex)
            coordinator.lastRouteCoordinatesCount = routeCoordinates.count
            coordinator.lastSegmentIndex = currentSegmentIndex
        } else if needsProgressUpdate {
            // 只更新已完成路线的覆盖物
            coordinator.updateProgressOverlay(mapView: mapView, routeCoordinates: routeCoordinates, currentSegmentIndex: currentSegmentIndex)
            coordinator.lastSegmentIndex = currentSegmentIndex
        }
        
        // 更新 OCM 图层
        if needsLayerUpdate || needsFullUpdate {
            coordinator.updateLayer(mapView: mapView, selectedLayer: selectedLayer)
            coordinator.lastSelectedLayer = selectedLayer
        }
        
        // 更新当前位置标注
        if needsLocationUpdate {
            coordinator.updateLocationAnnotation(mapView: mapView, currentLocation: currentLocation, isOffRoute: isOffRoute)
            coordinator.lastLocation = currentLocation
        } else if let location = currentLocation, !isOffRoute {
            // 即使位置对象相同，也需要跟随用户位置
            mapView.setCenter(location, animated: true)
        }
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }
    
    class Coordinator: NSObject, MAMapViewDelegate {
        var lastRouteCoordinatesCount: Int = -1
        var lastSegmentIndex: Int = -1
        var lastLocation: CLLocationCoordinate2D?
        var lastSelectedLayer: MapLayerMode = .standard
        
        private let fullRouteOverlayKey = "fullRoute"
        private let completedRouteOverlayKey = "completedRoute"
        private let ocmOverlayKey = "ocmContour"
        
        func updateLayer(mapView: MAMapView, selectedLayer: MapLayerMode) {
            // 移除旧的 OCM overlay
            let existingOCM = mapView.overlays.filter { ($0 as? OCMTileOverlay) != nil }
            if !existingOCM.isEmpty {
                mapView.removeOverlays(existingOCM)
            }
            
            // 添加新的 OCM overlay
            if selectedLayer == .contour {
                let ocmOverlay = OCMTileOverlay()
                mapView.add(ocmOverlay)
            }
        }
        
        func updateOverlays(mapView: MAMapView, routeCoordinates: [CLLocationCoordinate2D], currentSegmentIndex: Int) {
            mapView.removeOverlays(mapView.overlays)
            mapView.removeAnnotations(mapView.annotations)
            
            guard !routeCoordinates.isEmpty else { return }
            
            // 绘制完整路线（灰色）
            let fullPolyline = MAPolyline(coordinates: routeCoordinates, count: UInt(routeCoordinates.count))
            fullPolyline.title = fullRouteOverlayKey
            mapView.add(fullPolyline)
            
            // 绘制已走过的路线（绿色）
            if currentSegmentIndex > 0 && currentSegmentIndex < routeCoordinates.count {
                let completedCoords = Array(routeCoordinates[0..<currentSegmentIndex])
                let completedPolyline = MAPolyline(coordinates: completedCoords, count: UInt(completedCoords.count))
                completedPolyline.title = completedRouteOverlayKey
                mapView.add(completedPolyline)
            }
            
            // 添加起点标记
            let startAnnotation = MAPointAnnotation()
            startAnnotation.coordinate = routeCoordinates.first!
            startAnnotation.title = "起点"
            mapView.addAnnotation(startAnnotation)
            
            // 添加终点标记
            if routeCoordinates.count > 1 {
                let endAnnotation = MAPointAnnotation()
                endAnnotation.coordinate = routeCoordinates.last!
                endAnnotation.title = "终点"
                mapView.addAnnotation(endAnnotation)
            }
            
            // 仅首次设置地图区域
            if lastRouteCoordinatesCount == -1 {
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
        
        func updateProgressOverlay(mapView: MAMapView, routeCoordinates: [CLLocationCoordinate2D], currentSegmentIndex: Int) {
            // 移除旧的已完成路线覆盖物
            let overlaysToRemove = mapView.overlays.filter { ($0 as? MAPolyline)?.title == completedRouteOverlayKey }
            if !overlaysToRemove.isEmpty {
                mapView.removeOverlays(overlaysToRemove)
            }
            
            // 添加新的已完成路线
            if currentSegmentIndex > 0 && currentSegmentIndex < routeCoordinates.count {
                let completedCoords = Array(routeCoordinates[0..<currentSegmentIndex])
                let completedPolyline = MAPolyline(coordinates: completedCoords, count: UInt(completedCoords.count))
                completedPolyline.title = completedRouteOverlayKey
                mapView.add(completedPolyline)
            }
        }
        
        func updateLocationAnnotation(mapView: MAMapView, currentLocation: CLLocationCoordinate2D?, isOffRoute: Bool) {
            // 移除旧的位置标注
            let annotationsToRemove = mapView.annotations.filter { $0 is MAUserLocationAnnotation }
            if !annotationsToRemove.isEmpty {
                mapView.removeAnnotations(annotationsToRemove)
            }
            
            // 添加当前位置标记
            if let location = currentLocation {
                let annotation = MAUserLocationAnnotation()
                annotation.coordinate = location
                annotation.title = "当前位置"
                mapView.addAnnotation(annotation)
                
                if !isOffRoute {
                    mapView.setCenter(location, animated: true)
                }
            }
        }
        
        func mapView(_ mapView: MAMapView!, rendererFor overlay: MAOverlay!) -> MAOverlayRenderer! {
            guard let mapView = mapView, let overlay = overlay else { return nil }
            
            if let polyline = overlay as? MAPolyline {
                let renderer = MAPolylineRenderer(overlay: polyline)
                
                // 根据路线类型设置不同颜色
                if let title = polyline.title, title == completedRouteOverlayKey {
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
            guard let mapView = mapView, let annotation = annotation else { return nil }
            
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
