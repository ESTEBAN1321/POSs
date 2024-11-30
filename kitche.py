import sys
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QGridLayout,
    QScrollArea, QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon
from datetime import datetime
from PyQt5.QtMultimedia import QSound

class KitchenPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Panel de Cocina")
        
        # Obtener resolución de la pantalla
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        
        # Obtener el 50% de la resolución de la pantalla
        width = screen_geometry.width() // 2
        height = screen_geometry.height() // 2
        
        # Ajustar el tamaño de la ventana al 50% de la pantalla
        self.resize(width, height)
        
        self.setStyleSheet("background-color: #f8f9fa;")
        
        # Conexión a la base de datos
        self.db_connection = sqlite3.connect("pos.db")  # Cambia por tu base de datos
        self.db_connection.row_factory = sqlite3.Row
        self.cursor = self.db_connection.cursor()
        
        # Widget principal y diseño
        main_widget = QWidget()
        self.main_layout = QVBoxLayout(main_widget)
        
        # Encabezado
        header_layout = QHBoxLayout()  # Usar QHBoxLayout para colocar el título y el reloj
        header_label = QLabel("🍽️ Panel de Cocina")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setFont(QFont("Arial", 24, QFont.Bold))
        header_label.setStyleSheet("background-color: #343a40; color: white; padding: 15px;")
        header_label.setFixedHeight(70)

        # Crear el QLabel para la hora
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignRight)
        self.time_label.setFixedWidth(200)  # Establecer un ancho fijo de 200 píxeles
        self.time_label.setFont(QFont("Arial", 23, QFont.Bold))  # Fuente más pequeña y en negrita
        self.time_label.setStyleSheet("""
            color: #FF5733;  # Un color llamativo (puedes elegir el que desees)
            padding-right: 20px;
            font-size: 18px;  # Tamaño de fuente reducido
        """)


        header_layout.addWidget(header_label)
        header_layout.addWidget(self.time_label)

        self.main_layout.addLayout(header_layout)

        # Contenedor de tarjetas en scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_widget = QWidget()
        self.grid_layout = QGridLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setStyleSheet("border: none;")
        self.main_layout.addWidget(self.scroll_area)

        # Inicializar lista de pedidos previos
        self.previous_orders = set()
        
        # Ruta al archivo de sonido
        self.new_order_sound = QSound("new_order.wav")

        # Temporizador para actualización automática de pedidos
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_data)
        self.timer.start(500)  # Actualiza cada 500 ms
        
        # Temporizador para actualizar el reloj
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_time)
        self.clock_timer.start(1000)  # Actualiza cada segundo
        
        # Cargar datos inicialmente
        self.load_data()
        
        # Establecer el widget central
        self.setCentralWidget(main_widget)
        
        # Para controlar el zoom
        self.scale_factor = 1.0  # Factor de escala inicial

    def update_time(self):
        """Actualizar la hora en el encabezado en formato de 12 horas"""
        current_time = datetime.now().strftime("%I:%M %p")  # Hora en formato de 12 horas con AM/PM
        self.time_label.setText(current_time)


    def load_data(self):
        # Limpiar la cuadrícula actual
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Consultar pedidos pendientes con sus notas, excluyendo productos que empiezan con "B:"
        self.cursor.execute(""" 
            SELECT t.id, t.table_number, t.lugar, t.product_id, t.quantity, t.time_ordered, 
                p.name AS product_name, t.note
            FROM tickets t
            JOIN products p ON t.product_id = p.id
            WHERE t.status = 'pending' AND p.name NOT LIKE 'B:%'
        """)
        pending_orders = self.cursor.fetchall()

        # Detectar nuevos pedidos
        current_orders = set(order['id'] for order in pending_orders)
        new_orders = current_orders - self.previous_orders  # Pedidos que no estaban antes
        self.previous_orders = current_orders  # Actualizar lista de pedidos previos

        if new_orders:
            self.new_order_sound.play()  # Reproducir sonido al detectar nuevos pedidos

        # Agrupar pedidos pendientes por mesa y lugar
        pending_by_table = {}
        for order in pending_orders:
            key = (order['table_number'], order['lugar'])
            if key not in pending_by_table:
                pending_by_table[key] = []
            pending_by_table[key].append(order)

        # Generar tarjetas en un arreglo de 4 columnas por N filas
        row, col = 0, 0
        for (table_number, location), orders in pending_by_table.items():
            table_card = self.create_table_card(table_number, location, orders)
            self.grid_layout.addWidget(table_card, row, col)

            # Mover a la siguiente celda
            col += 1
            if col >= 4:  # Limitar a 4 columnas
                col = 0
                row += 1
    def create_table_card(self, table_number, location, orders):
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("""
            background-color: white; border: 1px solid #ddd; border-radius: 8px;
            padding: 15px;
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        card_layout = QVBoxLayout(card)

        # Hora del primer pedido
        first_order_time = orders[0]['time_ordered']
        order_datetime = datetime.strptime(first_order_time, "%Y-%m-%d %H:%M:%S")
        formatted_time = order_datetime.strftime("%I:%M %p")

        # Encabezado de la tarjeta (sin "Nuevo" aquí)
        title = QLabel(f"🪑 Mesa {table_number} - {location} ({formatted_time})")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #343a40; margin-bottom: 10px;")
        title.setFixedHeight(90)
        card_layout.addWidget(title)

        # Consolidar los pedidos con "Nuevo" al lado de los que son recientes
        orders_text = ""
        for order in orders:
            # Comprobar si este pedido es nuevo
            is_new_order = datetime.strptime(order['time_ordered'], "%Y-%m-%d %H:%M:%S") > order_datetime
            order_text = f"<span style='color: #555;'>🍴 {order['product_name']} -- <span style='color: #EF0107;'>(x{order['quantity']})</span></span>"
            
            if is_new_order:
                # Convertir la hora a formato de 12 horas
                order_time = datetime.strptime(order['time_ordered'], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
                order_text += f" <span style='font-size: 0.7em; color: #888;'>({order_time})</span>"

                # Marcar el pedido como nuevo
                order_text += " <span style='color: red;'>Nuevo</span>"
            
            orders_text += f"{order_text}<br>"

        # Consolidar notas únicas al final
        seen_notes = set()
        notes_text = ""
        for order in orders:
            if order['note'] and order['note'] not in seen_notes:
                seen_notes.add(order['note'])
                notes_text += f"📝 <span style='color: #ff5722;'>Nota: {order['note']}</span><br>"

        # Combinar pedidos y notas en un solo texto
        combined_text = f"{orders_text.strip()}<br>{notes_text.strip()}"

        # Crear un QLabel con formato HTML para pedidos y notas
        orders_label = QLabel()
        orders_label.setText(f"<html><body>{combined_text}</body></html>")
        orders_label.setFont(QFont("Arial", 12))
        orders_label.setStyleSheet("color: #555;")
        orders_label.setWordWrap(True)
        orders_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        card_layout.addWidget(orders_label)

        # Botón de acción
        complete_button = QPushButton("Completar Todo")
        complete_button.setStyleSheet("""
            background-color: #28a745; color: white; border: none; padding: 8px 12px;
            border-radius: 5px; font-size: 12px;
        """)
        complete_button.clicked.connect(lambda _, orders=orders: self.complete_all_orders(orders))
        card_layout.addWidget(complete_button, alignment=Qt.AlignRight)

        return card




    def complete_all_orders(self, orders):
        for order in orders:
            self.cursor.execute("UPDATE tickets SET status = 'completed' WHERE id = ?", (order['id'],))
        self.db_connection.commit()
        self.load_data()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KitchenPanel()
    window.show()
    sys.exit(app.exec_())
