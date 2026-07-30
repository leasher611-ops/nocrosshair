#!/usr/bin/env python3
"""
Advanced Recoil Visualizer Widget

Features:
- Real-time recoil pattern animation
- Bezier curve visualization
- Multi-weapon comparison
- Fire rate simulation
- Performance metrics display
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt6.QtCore import QRect
from typing import List, Tuple, Dict, Any, Optional
import math


class RecoilVisualizerAdvanced(QWidget):
    """Advanced recoil pattern visualization widget"""
    
    pattern_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        
        # Recoil pattern data
        self.pattern_points: List[Tuple[int, int]] = []
        self.current_tick = 0
        self.total_ticks = 60
        self.is_animating = False
        
        # Visualization settings
        self.scale = 2.0  # pixels per unit
        self.center_x = 300
        self.center_y = 200
        
        # Animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._on_animation_tick)
        self.animation_speed = 1  # 1x speed
        
        # Performance metrics
        self.metrics = {
            'max_deviation': 0,
            'avg_deviation': 0,
            'smoothness': 0.0,
        }
        
        self.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444;")
    
    def set_pattern(self, points: List[Tuple[int, int]]) -> None:
        """Set recoil pattern to visualize"""
        self.pattern_points = points
        self.total_ticks = len(points)
        self.current_tick = 0
        self._calculate_metrics()
        self.update()
    
    def start_animation(self) -> None:
        """Start pattern animation"""
        self.is_animating = True
        self.current_tick = 0
        self.animation_timer.start(16)  # ~60 FPS
    
    def stop_animation(self) -> None:
        """Stop pattern animation"""
        self.is_animating = False
        self.animation_timer.stop()
        self.current_tick = 0
        self.update()
    
    def _on_animation_tick(self) -> None:
        """Handle animation tick"""
        self.current_tick += self.animation_speed
        if self.current_tick >= self.total_ticks:
            self.current_tick = 0
        self.update()
    
    def paintEvent(self, event):
        """Paint the recoil visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background grid
        self._draw_grid(painter)
        
        # Draw recoil pattern
        self._draw_pattern(painter)
        
        # Draw current position
        if self.is_animating and self.current_tick < len(self.pattern_points):
            self._draw_current_position(painter)
        
        # Draw metrics
        self._draw_metrics(painter)
    
    def _draw_grid(self, painter: QPainter) -> None:
        """Draw background grid"""
        pen = QPen(QColor(60, 60, 60))
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Grid spacing
        grid_size = 50
        
        for x in range(0, self.width(), grid_size):
            painter.drawLine(x, 0, x, self.height())
        
        for y in range(0, self.height(), grid_size):
            painter.drawLine(0, y, self.width(), y)
        
        # Draw center crosshair
        pen = QPen(QColor(100, 100, 100))
        pen.setWidth(2)
        painter.setPen(pen)
        
        painter.drawLine(self.center_x - 10, self.center_y, self.center_x + 10, self.center_y)
        painter.drawLine(self.center_x, self.center_y - 10, self.center_x, self.center_y + 10)
    
    def _draw_pattern(self, painter: QPainter) -> None:
        """Draw recoil pattern curve"""
        if not self.pattern_points or len(self.pattern_points) < 2:
            return
        
        pen = QPen(QColor(0, 255, 136))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Draw pattern line
        for i in range(len(self.pattern_points) - 1):
            y1, x1 = self.pattern_points[i]
            y2, x2 = self.pattern_points[i + 1]
            
            # Convert to screen coordinates
            screen_x1 = self.center_x + x1 * self.scale
            screen_y1 = self.center_y + y1 * self.scale
            screen_x2 = self.center_x + x2 * self.scale
            screen_y2 = self.center_y + y2 * self.scale
            
            painter.drawLine(int(screen_x1), int(screen_y1), int(screen_x2), int(screen_y2))
        
        # Draw pattern points
        brush = QBrush(QColor(0, 255, 136))
        for i, (y, x) in enumerate(self.pattern_points):
            screen_x = self.center_x + x * self.scale
            screen_y = self.center_y + y * self.scale
            
            # Color intensity based on position in pattern
            intensity = int(100 + 155 * (i / max(len(self.pattern_points) - 1, 1)))
            color = QColor(0, intensity, 136)
            
            painter.setBrush(color)
            painter.setPen(QPen(color))
            painter.drawEllipse(int(screen_x) - 3, int(screen_y) - 3, 6, 6)
    
    def _draw_current_position(self, painter: QPainter) -> None:
        """Draw current animated position"""
        if self.current_tick >= len(self.pattern_points):
            return
        
        y, x = self.pattern_points[int(self.current_tick)]
        screen_x = self.center_x + x * self.scale
        screen_y = self.center_y + y * self.scale
        
        # Draw current position marker
        pen = QPen(QColor(255, 100, 100))
        pen.setWidth(3)
        painter.setPen(pen)
        
        painter.drawEllipse(int(screen_x) - 8, int(screen_y) - 8, 16, 16)
        
        # Draw trail
        pen = QPen(QColor(255, 100, 100, 100))
        pen.setWidth(1)
        painter.setPen(pen)
        
        for i in range(max(0, int(self.current_tick) - 10), int(self.current_tick)):
            if i < len(self.pattern_points):
                y1, x1 = self.pattern_points[i]
                y2, x2 = self.pattern_points[i + 1]
                
                screen_x1 = self.center_x + x1 * self.scale
                screen_y1 = self.center_y + y1 * self.scale
                screen_x2 = self.center_x + x2 * self.scale
                screen_y2 = self.center_y + y2 * self.scale
                
                painter.drawLine(int(screen_x1), int(screen_y1), int(screen_x2), int(screen_y2))
    
    def _draw_metrics(self, painter: QPainter) -> None:
        """Draw performance metrics"""
        font = QFont("Courier")
        font.setPointSize(9)
        painter.setFont(font)
        
        metrics_text = [
            f"Max Deviation: {self.metrics['max_deviation']:.1f}",
            f"Avg Deviation: {self.metrics['avg_deviation']:.1f}",
            f"Smoothness: {self.metrics['smoothness']:.2f}",
            f"Ticks: {self.total_ticks}",
        ]
        
        if self.is_animating:
            metrics_text.append(f"Current: {int(self.current_tick)}/{self.total_ticks}")
        
        y_offset = 20
        for text in metrics_text:
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(20, y_offset, text)
            y_offset += 20
    
    def _calculate_metrics(self) -> None:
        """Calculate recoil pattern metrics"""
        if not self.pattern_points:
            return
        
        # Max deviation
        max_dev = 0
        for y, x in self.pattern_points:
            dev = math.sqrt(x*x + y*y)
            max_dev = max(max_dev, dev)
        
        self.metrics['max_deviation'] = max_dev
        
        # Average deviation
        avg_dev = sum(math.sqrt(x*x + y*y) for y, x in self.pattern_points) / len(self.pattern_points)
        self.metrics['avg_deviation'] = avg_dev
        
        # Smoothness (inverse of variance in changes)
        if len(self.pattern_points) > 1:
            changes = []
            for i in range(len(self.pattern_points) - 1):
                y1, x1 = self.pattern_points[i]
                y2, x2 = self.pattern_points[i + 1]
                change = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                changes.append(change)
            
            avg_change = sum(changes) / len(changes)
            variance = sum((c - avg_change)**2 for c in changes) / len(changes)
            
            # Smoothness is inverse of variance (normalized)
            self.metrics['smoothness'] = 1.0 / (1.0 + variance / 100.0)


class RecoilComparisonWidget(QWidget):
    """Compare multiple recoil patterns side-by-side"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 500)
        
        layout = QVBoxLayout()
        
        # Pattern selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Weapon 1:"))
        self.weapon1_combo = QComboBox()
        selector_layout.addWidget(self.weapon1_combo)
        
        selector_layout.addWidget(QLabel("Weapon 2:"))
        self.weapon2_combo = QComboBox()
        selector_layout.addWidget(self.weapon2_combo)
        
        layout.addLayout(selector_layout)
        
        # Visualizers
        viz_layout = QHBoxLayout()
        self.viz1 = RecoilVisualizerAdvanced()
        self.viz2 = RecoilVisualizerAdvanced()
        viz_layout.addWidget(self.viz1)
        viz_layout.addWidget(self.viz2)
        
        layout.addLayout(viz_layout)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self._on_play)
        control_layout.addWidget(self.play_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_stop)
        control_layout.addWidget(self.stop_button)
        
        layout.addLayout(control_layout)
        
        self.setLayout(layout)
    
    def _on_play(self) -> None:
        """Start animation"""
        self.viz1.start_animation()
        self.viz2.start_animation()
    
    def _on_stop(self) -> None:
        """Stop animation"""
        self.viz1.stop_animation()
        self.viz2.stop_animation()
