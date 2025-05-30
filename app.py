from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import MySQLdb.cursors
import re

app = Flask(__name__)

# Configuración de MySQL para XAMPP
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'  
app.config['MYSQL_DB'] = 'proyect_mc'
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'

mysql = MySQL(app)

# Función auxiliar para obtener conexión
def get_db_connection():
    return mysql.connection

# ===== DASHBOARD =====
@app.route('/')
def index():
    """Dashboard principal"""
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Obtener estadísticas
        cursor.execute("SELECT COUNT(*) as total FROM pacientes")
        total_pacientes = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM medicos")
        total_medicos = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM citas WHERE DATE(fecha_hora) = CURDATE()")
        citas_hoy = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM citas WHERE estado = 'programada'")
        citas_pendientes = cursor.fetchone()['total']
        
        # Obtener citas recientes
        cursor.execute("""
            SELECT c.id, 
                   CONCAT(p.nombres, ' ', p.apellidos) as paciente,
                   CONCAT('Dr. ', m.nombre, ' ', m.apellido) as medico,
                   e.nombre as especialidad,
                   c.fecha_hora,
                   c.estado
            FROM citas c
            JOIN pacientes p ON c.paciente_id = p.id
            JOIN medicos m ON c.medico_id = m.id
            JOIN especialidades e ON m.especialidad_id = e.id
            ORDER BY c.fecha_hora DESC
            LIMIT 5
        """)
        citas_recientes = cursor.fetchall()
        
        cursor.close()
        
        stats = {
            'total_pacientes': total_pacientes,
            'total_medicos': total_medicos,
            'citas_hoy': citas_hoy,
            'citas_pendientes': citas_pendientes
        }
        
        return render_template('index.html', stats=stats, citas_recientes=citas_recientes)
    
    except Exception as e:
        flash(f'Error al cargar el dashboard: {str(e)}', 'error')
        return render_template('index.html', stats={}, citas_recientes=[])

# ===== PACIENTES =====
@app.route('/pacientes')
def pacientes():
    """Lista de pacientes"""
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT p.*, u.usuario, u.email 
            FROM pacientes p 
            JOIN usuarios u ON p.id = u.id
            ORDER BY p.apellidos, p.nombres
        """)
        pacientes_list = cursor.fetchall()
        cursor.close()
        
        return render_template('pacientes/lista.html', pacientes=pacientes_list)
    
    except Exception as e:
        flash(f'Error al cargar pacientes: {str(e)}', 'error')
        return render_template('pacientes/lista.html', pacientes=[])

@app.route('/pacientes/nuevo', methods=['GET', 'POST'])
def nuevo_paciente():
    """Agregar nuevo paciente"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombres = request.form['nombres']
            apellidos = request.form['apellidos']
            fecha_nacimiento = request.form['fecha_nacimiento']
            telefono = request.form['telefono']
            direccion = request.form['direccion']
            usuario = request.form['usuario']
            email = request.form['email']
            password = request.form['password']
            
            cursor = mysql.connection.cursor()
            
            # Verificar si el usuario ya existe
            cursor.execute("SELECT id FROM usuarios WHERE usuario = %s OR email = %s", (usuario, email))
            if cursor.fetchone():
                flash('El usuario o email ya existe', 'error')
                return render_template('pacientes/nuevo.html')
            
            # Obtener ID del rol paciente
            cursor.execute("SELECT id FROM roles WHERE nombre = 'paciente'")
            rol_result = cursor.fetchone()
            if not rol_result:
                # Crear rol paciente si no existe
                cursor.execute("INSERT INTO roles (nombre) VALUES ('paciente')")
                mysql.connection.commit()
                rol_id = cursor.lastrowid
            else:
                rol_id = rol_result[0]
            
            # Insertar usuario
            hash_password = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO usuarios (rol_id, usuario, email, hash_clave) 
                VALUES (%s, %s, %s, %s)
            """, (rol_id, usuario, email, hash_password))
            
            usuario_id = cursor.lastrowid
            
            # Insertar paciente
            cursor.execute("""
                INSERT INTO pacientes (id, nombres, apellidos, fecha_nacimiento, telefono, direccion) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (usuario_id, nombres, apellidos, fecha_nacimiento, telefono, direccion))
            
            mysql.connection.commit()
            cursor.close()
            
            flash('Paciente agregado exitosamente', 'success')
            return redirect(url_for('pacientes'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al agregar paciente: {str(e)}', 'error')
            return render_template('pacientes/nuevo.html')
    
    return render_template('pacientes/nuevo.html')

@app.route('/pacientes/editar/<int:id>', methods=['GET', 'POST'])
def editar_paciente(id):
    """Editar paciente existente"""
    if request.method == 'POST':
        try:
            nombres = request.form['nombres']
            apellidos = request.form['apellidos']
            fecha_nacimiento = request.form['fecha_nacimiento']
            telefono = request.form['telefono']
            direccion = request.form['direccion']
            email = request.form['email']
            
            cursor = mysql.connection.cursor()
            
            # Actualizar paciente
            cursor.execute("""
                UPDATE pacientes 
                SET nombres = %s, apellidos = %s, fecha_nacimiento = %s, 
                    telefono = %s, direccion = %s 
                WHERE id = %s
            """, (nombres, apellidos, fecha_nacimiento, telefono, direccion, id))
            
            # Actualizar email del usuario
            cursor.execute("UPDATE usuarios SET email = %s WHERE id = %s", (email, id))
            
            mysql.connection.commit()
            cursor.close()
            
            flash('Paciente actualizado exitosamente', 'success')
            return redirect(url_for('pacientes'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al actualizar paciente: {str(e)}', 'error')
    
    # Obtener datos del paciente
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT p.*, u.usuario, u.email 
            FROM pacientes p 
            JOIN usuarios u ON p.id = u.id 
            WHERE p.id = %s
        """, (id,))
        paciente = cursor.fetchone()
        cursor.close()
        
        if not paciente:
            flash('Paciente no encontrado', 'error')
            return redirect(url_for('pacientes'))
        
        return render_template('pacientes/editar.html', paciente=paciente)
    
    except Exception as e:
        flash(f'Error al cargar paciente: {str(e)}', 'error')
        return redirect(url_for('pacientes'))

@app.route('/pacientes/eliminar/<int:id>')
def eliminar_paciente(id):
    """Eliminar paciente"""
    try:
        cursor = mysql.connection.cursor()
        
        # Verificar si tiene citas
        cursor.execute("SELECT COUNT(*) as total FROM citas WHERE paciente_id = %s", (id,))
        citas_count = cursor.fetchone()[0]
        
        if citas_count > 0:
            flash('No se puede eliminar el paciente porque tiene citas asociadas', 'error')
            return redirect(url_for('pacientes'))
        
        # Eliminar paciente y usuario
        cursor.execute("DELETE FROM pacientes WHERE id = %s", (id,))
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
        
        mysql.connection.commit()
        cursor.close()
        
        flash('Paciente eliminado exitosamente', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error al eliminar paciente: {str(e)}', 'error')
    
    return redirect(url_for('pacientes'))

# ===== MÉDICOS =====
@app.route('/medicos')
def medicos():
    """Lista de médicos"""
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT m.*, u.usuario, u.email, e.nombre as especialidad
            FROM medicos m 
            JOIN usuarios u ON m.id = u.id
            JOIN especialidades e ON m.especialidad_id = e.id
            ORDER BY m.apellido, m.nombre
        """)
        medicos_list = cursor.fetchall()
        cursor.close()
        
        return render_template('medicos/lista.html', medicos=medicos_list)
    
    except Exception as e:
        flash(f'Error al cargar médicos: {str(e)}', 'error')
        return render_template('medicos/lista.html', medicos=[])

@app.route('/medicos/nuevo', methods=['GET', 'POST'])
def nuevo_medico():
    """Agregar nuevo médico"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            usuario = request.form['usuario']
            email = request.form['email']
            password = request.form['password']
            especialidad_id = request.form['especialidad_id']
            num_licencia = request.form['num_licencia']
            telefono = request.form['telefono']
            
            cursor = mysql.connection.cursor()
            
            # Verificar si el usuario ya existe
            cursor.execute("SELECT id FROM usuarios WHERE usuario = %s OR email = %s", (usuario, email))
            if cursor.fetchone():
                flash('El usuario o email ya existe', 'error')
                return redirect(url_for('nuevo_medico'))
            
            # Verificar si la licencia ya existe
            cursor.execute("SELECT id FROM medicos WHERE num_licencia = %s", (num_licencia,))
            if cursor.fetchone():
                flash('El número de licencia ya existe', 'error')
                return redirect(url_for('nuevo_medico'))
            
            # Obtener ID del rol médico
            cursor.execute("SELECT id FROM roles WHERE nombre = 'medico'")
            rol_result = cursor.fetchone()
            if not rol_result:
                # Crear rol médico si no existe
                cursor.execute("INSERT INTO roles (nombre) VALUES ('medico')")
                mysql.connection.commit()
                rol_id = cursor.lastrowid
            else:
                rol_id = rol_result[0]
            
            # Insertar usuario
            hash_password = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO usuarios (rol_id, usuario, email, hash_clave) 
                VALUES (%s, %s, %s, %s)
            """, (rol_id, usuario, email, hash_password))
            
            usuario_id = cursor.lastrowid
            
            # Insertar médico con nombre y apellido
            cursor.execute("""
                INSERT INTO medicos (id, nombre, apellido, especialidad_id, num_licencia, telefono) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (usuario_id, nombre, apellido, especialidad_id, num_licencia, telefono))
            
            mysql.connection.commit()
            cursor.close()
            
            flash('Médico agregado exitosamente', 'success')
            return redirect(url_for('medicos'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al agregar médico: {str(e)}', 'error')
    
    # Obtener especialidades para el formulario
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM especialidades ORDER BY nombre")
        especialidades = cursor.fetchall()
        cursor.close()
    except:
        especialidades = []
    
    return render_template('medicos/nuevo.html', especialidades=especialidades)

@app.route('/medicos/editar/<int:id>', methods=['GET', 'POST'])
def editar_medico(id):
    """Editar médico existente"""
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            email = request.form['email']
            especialidad_id = request.form['especialidad_id']
            num_licencia = request.form['num_licencia']
            telefono = request.form['telefono']
            
            cursor = mysql.connection.cursor()
            
            # Verificar si la licencia ya existe en otro médico
            cursor.execute("SELECT id FROM medicos WHERE num_licencia = %s AND id != %s", (num_licencia, id))
            if cursor.fetchone():
                flash('El número de licencia ya existe', 'error')
                return redirect(url_for('editar_medico', id=id))
            
            # Actualizar médico con nombre y apellido
            cursor.execute("""
                UPDATE medicos 
                SET nombre = %s, apellido = %s, especialidad_id = %s, num_licencia = %s, telefono = %s 
                WHERE id = %s
            """, (nombre, apellido, especialidad_id, num_licencia, telefono, id))
            
            # Actualizar email del usuario
            cursor.execute("UPDATE usuarios SET email = %s WHERE id = %s", (email, id))
            
            mysql.connection.commit()
            cursor.close()
            
            flash('Médico actualizado exitosamente', 'success')
            return redirect(url_for('medicos'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al actualizar médico: {str(e)}', 'error')
    
    # Obtener datos del médico y especialidades
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute("""
            SELECT m.*, u.usuario, u.email, e.nombre as especialidad_nombre
            FROM medicos m 
            JOIN usuarios u ON m.id = u.id
            JOIN especialidades e ON m.especialidad_id = e.id
            WHERE m.id = %s
        """, (id,))
        medico = cursor.fetchone()
        
        cursor.execute("SELECT * FROM especialidades ORDER BY nombre")
        especialidades = cursor.fetchall()
        
        cursor.close()
        
        if not medico:
            flash('Médico no encontrado', 'error')
            return redirect(url_for('medicos'))
        
        return render_template('medicos/editar.html', medico=medico, especialidades=especialidades)
    
    except Exception as e:
        flash(f'Error al cargar médico: {str(e)}', 'error')
        return redirect(url_for('medicos'))

@app.route('/medicos/eliminar/<int:id>')
def eliminar_medico(id):
    """Eliminar médico"""
    try:
        cursor = mysql.connection.cursor()
        
        # Verificar si tiene citas
        cursor.execute("SELECT COUNT(*) as total FROM citas WHERE medico_id = %s", (id,))
        citas_count = cursor.fetchone()[0]
        
        if citas_count > 0:
            flash('No se puede eliminar el médico porque tiene citas asociadas', 'error')
            return redirect(url_for('medicos'))
        
        # Eliminar médico y usuario
        cursor.execute("DELETE FROM medicos WHERE id = %s", (id,))
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
        
        mysql.connection.commit()
        cursor.close()
        
        flash('Médico eliminado exitosamente', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error al eliminar médico: {str(e)}', 'error')
    
    return redirect(url_for('medicos'))

# ===== CITAS =====
@app.route('/citas')
def citas():
    """Lista de citas"""
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT c.*, 
                   CONCAT(p.nombres, ' ', p.apellidos) as paciente,
                   CONCAT('Dr. ', m.nombre, ' ', m.apellido) as medico,
                   e.nombre as especialidad
            FROM citas c
            JOIN pacientes p ON c.paciente_id = p.id
            JOIN medicos m ON c.medico_id = m.id
            JOIN especialidades e ON m.especialidad_id = e.id
            ORDER BY c.fecha_hora DESC
        """)
        citas_list = cursor.fetchall()
        cursor.close()
        
        return render_template('citas/lista.html', citas=citas_list)
    
    except Exception as e:
        flash(f'Error al cargar citas: {str(e)}', 'error')
        return render_template('citas/lista.html', citas=[])

@app.route('/citas/nueva', methods=['GET', 'POST'])
def nueva_cita():
    """Agregar nueva cita"""
    if request.method == 'POST':
        try:
            paciente_id = request.form['paciente_id']
            medico_id = request.form['medico_id']
            fecha_hora = request.form['fecha_hora']
            notas = request.form['notas']
            
            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO citas (paciente_id, medico_id, fecha_hora, notas) 
                VALUES (%s, %s, %s, %s)
            """, (paciente_id, medico_id, fecha_hora, notas))
            
            mysql.connection.commit()
            cursor.close()
            
            flash('Cita programada exitosamente', 'success')
            return redirect(url_for('citas'))
            
        except Exception as e:
            flash(f'Error al programar cita: {str(e)}', 'error')
    
    # Obtener pacientes y médicos para el formulario
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute("""
            SELECT p.id, CONCAT(p.nombres, ' ', p.apellidos) as nombre_completo 
            FROM pacientes p 
            ORDER BY p.apellidos, p.nombres
        """)
        pacientes = cursor.fetchall()
        
        cursor.execute("""
            SELECT m.id, CONCAT('Dr. ', m.nombre, ' ', m.apellido, ' - ', e.nombre) as nombre_completo 
            FROM medicos m 
            JOIN especialidades e ON m.especialidad_id = e.id
            ORDER BY m.apellido, m.nombre
        """)
        medicos = cursor.fetchall()
        
        cursor.close()
    except:
        pacientes = []
        medicos = []
    
    return render_template('citas/nueva.html', pacientes=pacientes, medicos=medicos)

@app.route('/citas/editar/<int:id>', methods=['GET', 'POST'])
def editar_cita(id):
    """Editar cita existente"""
    if request.method == 'POST':
        try:
            paciente_id = request.form['paciente_id']
            medico_id = request.form['medico_id']
            fecha_hora = request.form['fecha_hora']
            estado = request.form['estado']
            notas = request.form['notas']
            
            cursor = mysql.connection.cursor()
            cursor.execute("""
                UPDATE citas 
                SET paciente_id = %s, medico_id = %s, fecha_hora = %s, 
                    estado = %s, notas = %s 
                WHERE id = %s
            """, (paciente_id, medico_id, fecha_hora, estado, notas, id))
            
            mysql.connection.commit()
            cursor.close()
            
            flash('Cita actualizada exitosamente', 'success')
            return redirect(url_for('citas'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al actualizar cita: {str(e)}', 'error')
    
    # Obtener datos de la cita, pacientes y médicos
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute("SELECT * FROM citas WHERE id = %s", (id,))
        cita = cursor.fetchone()
        
        cursor.execute("""
            SELECT p.id, CONCAT(p.nombres, ' ', p.apellidos) as nombre_completo 
            FROM pacientes p 
            ORDER BY p.apellidos, p.nombres
        """)
        pacientes = cursor.fetchall()
        
        cursor.execute("""
            SELECT m.id, CONCAT('Dr. ', m.nombre, ' ', m.apellido, ' - ', e.nombre) as nombre_completo 
            FROM medicos m 
            JOIN especialidades e ON m.especialidad_id = e.id
            ORDER BY m.apellido, m.nombre
        """)
        medicos = cursor.fetchall()
        
        cursor.close()
        
        if not cita:
            flash('Cita no encontrada', 'error')
            return redirect(url_for('citas'))
        
        return render_template('citas/editar.html', cita=cita, pacientes=pacientes, medicos=medicos)
    
    except Exception as e:
        flash(f'Error al cargar cita: {str(e)}', 'error')
        return redirect(url_for('citas'))

@app.route('/citas/eliminar/<int:id>')
def eliminar_cita(id):
    """Eliminar cita"""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM citas WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()
        
        flash('Cita eliminada exitosamente', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error al eliminar cita: {str(e)}', 'error')
    
    return redirect(url_for('citas'))

@app.route('/citas/actualizar_estado/<int:cita_id>/<estado>')
def actualizar_estado_cita(cita_id, estado):
    """Actualizar estado de una cita"""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE citas SET estado = %s WHERE id = %s", (estado, cita_id))
        mysql.connection.commit()
        cursor.close()
        
        flash(f'Estado de la cita actualizado a {estado}', 'success')
    except Exception as e:
        flash(f'Error al actualizar estado: {str(e)}', 'error')
    
    return redirect(url_for('citas'))

# ===== ESPECIALIDADES =====
@app.route('/especialidades')
def especialidades():
    """Lista de especialidades"""
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT e.*, COUNT(m.id) as medicos_count 
            FROM especialidades e 
            LEFT JOIN medicos m ON e.id = m.especialidad_id 
            GROUP BY e.id 
            ORDER BY e.nombre
        """)
        especialidades_list = cursor.fetchall()
        cursor.close()
        
        return render_template('especialidades/lista.html', especialidades=especialidades_list)
    
    except Exception as e:
        flash(f'Error al cargar especialidades: {str(e)}', 'error')
        return render_template('especialidades/lista.html', especialidades=[])

@app.route('/especialidades/nueva', methods=['GET', 'POST'])
def nueva_especialidad():
    """Agregar nueva especialidad"""
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            
            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO especialidades (nombre, descripcion) 
                VALUES (%s, %s)
            """, (nombre, descripcion))
            
            mysql.connection.commit()
            cursor.close()
            
            flash('Especialidad agregada exitosamente', 'success')
            return redirect(url_for('especialidades'))
            
        except Exception as e:
            flash(f'Error al agregar especialidad: {str(e)}', 'error')
    
    return render_template('especialidades/nueva.html')

@app.route('/especialidades/editar/<int:id>', methods=['GET', 'POST'])
def editar_especialidad(id):
    """Editar especialidad existente"""
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            
            cursor = mysql.connection.cursor()
            cursor.execute("""
                UPDATE especialidades 
                SET nombre = %s, descripcion = %s 
                WHERE id = %s
            """, (nombre, descripcion, id))
            
            mysql.connection.commit()
            cursor.close()
            
            flash('Especialidad actualizada exitosamente', 'success')
            return redirect(url_for('especialidades'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al actualizar especialidad: {str(e)}', 'error')
    
    # Obtener datos de la especialidad
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM especialidades WHERE id = %s", (id,))
        especialidad = cursor.fetchone()
        cursor.close()
        
        if not especialidad:
            flash('Especialidad no encontrada', 'error')
            return redirect(url_for('especialidades'))
        
        return render_template('especialidades/editar.html', especialidad=especialidad)
    
    except Exception as e:
        flash(f'Error al cargar especialidad: {str(e)}', 'error')
        return redirect(url_for('especialidades'))

@app.route('/especialidades/eliminar/<int:id>')
def eliminar_especialidad(id):
    """Eliminar especialidad"""
    try:
        cursor = mysql.connection.cursor()
        
        # Verificar si tiene médicos asociados
        cursor.execute("SELECT COUNT(*) as total FROM medicos WHERE especialidad_id = %s", (id,))
        medicos_count = cursor.fetchone()[0]
        
        if medicos_count > 0:
            flash('No se puede eliminar la especialidad porque tiene médicos asociados', 'error')
            return redirect(url_for('especialidades'))
        
        cursor.execute("DELETE FROM especialidades WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()
        
        flash('Especialidad eliminada exitosamente', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error al eliminar especialidad: {str(e)}', 'error')
    
    return redirect(url_for('especialidades'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
