from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors

app = Flask(__name__)

# Configuración para XAMPP (
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'  
app.config['MYSQL_DB'] = 'proyect_mc'
app.config['SECRET_KEY'] = 'clave_temporal'

mysql = MySQL(app)

@app.route('/')
def index():
    """Página principal - Dashboard básico"""
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Contar pacientes
        cursor.execute("SELECT COUNT(*) as total FROM pacientes")
        total_pacientes = cursor.fetchone()['total']
        
        # Contar médicos
        cursor.execute("SELECT COUNT(*) as total FROM medicos")
        total_medicos = cursor.fetchone()['total']
        
        # Contar citas
        cursor.execute("SELECT COUNT(*) as total FROM citas")
        total_citas = cursor.fetchone()['total']
        
        # Contar especialidades
        cursor.execute("SELECT COUNT(*) as total FROM especialidades")
        total_especialidades = cursor.fetchone()['total']
        
        cursor.close()
        
        stats = {
            'pacientes': total_pacientes,
            'medicos': total_medicos,
            'citas': total_citas,
            'especialidades': total_especialidades
        }
        
        return render_template('index.html', stats=stats)
        
    except Exception as e:
        flash(f'Error de conexión: {str(e)}', 'error')
        # Si hay error, mostrar stats vacías
        stats = {'pacientes': 0, 'medicos': 0, 'citas': 0, 'especialidades': 0}
        return render_template('index.html', stats=stats)

@app.route('/pacientes')
def pacientes():
    """Lista de pacientes"""
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT p.*, u.usuario, u.email 
            FROM pacientes p 
            LEFT JOIN usuarios u ON p.id = u.id
            ORDER BY p.apellidos, p.nombres
        """)
        pacientes_list = cursor.fetchall()
        cursor.close()
        
        return render_template('pacientes.html', pacientes=pacientes_list)
        
    except Exception as e:
        flash(f'Error al cargar pacientes: {str(e)}', 'error')
        return render_template('pacientes.html', pacientes=[])

@app.route('/especialidades')
def especialidades():
    """Lista de especialidades"""
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM especialidades ORDER BY nombre")
        especialidades_list = cursor.fetchall()
        cursor.close()
        
        return render_template('especialidades.html', especialidades=especialidades_list)
        
    except Exception as e:
        flash(f'Error al cargar especialidades: {str(e)}', 'error')
        return render_template('especialidades.html', especialidades=[])

@app.route('/nueva_especialidad', methods=['GET', 'POST'])
def nueva_especialidad():
    """Agregar nueva especialidad - Funcionalidad básica"""
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
    
    return render_template('nueva_especialidad.html')

@app.route('/test_conexion')
def test_conexion():
    """Ruta para probar la conexión a la base de datos"""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return "<h2> Conexión exitosa a MySQL</h2><p>La base de datos está funcionando correctamente.</p>"
        else:
            return "<h2> Error en la consulta</h2>"
            
    except Exception as e:
        return f"<h2> Error de conexión</h2><p>{str(e)}</p>"

if __name__ == '__main__':
    print(" Iniciando Sistema Médico...")
    print(" Dashboard: http://localhost:5000")
    print(" Test conexión: http://localhost:5000/test_conexion")
    app.run(debug=True, host='0.0.0.0', port=5000)