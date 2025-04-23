#!/usr/bin/env python3
from os import system, path, chmod
from subprocess import check_output, STDOUT, CalledProcessError, run
from argparse import ArgumentParser
from sys import exit, argv
from rich.console import Console
from rich.markdown import Markdown
from time import sleep, time
import threading
import asyncio
from google import genai
import os

console = Console()

def clear_screen():
    system("clear")
    console.print("[bold green]~ ManExplainer v1.0.0 ~[/bold green]\n")

def delayed_print(text, delay=0.5):
    print(text)
    sleep(delay)

def install_manexplainer():
    """Install manexplainer as a system command with proper line ending handling"""
    script_path = path.abspath(__file__)
    install_path = "/usr/local/bin/manexplainer"
    
    clear_screen()
    console.print("[bold]Instalando ManExplainer...[/bold]\n")
    
    try:
        # Leer el contenido del script actual
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Asegurar que tenga el shebang correcto y formato de línea Unix
        lines = content.replace('\r\n', '\n').split('\n')
        
        # Comprobar si la primera línea es el shebang
        if not lines[0].startswith('#!/usr/bin/env python3'):
            lines.insert(0, '#!/usr/bin/env python3')
        
        # Crear archivo temporal con el contenido correcto
        temp_file = "/tmp/manexplainer_temp"
        with open(temp_file, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines))
        
        # Instalar usando sudo
        print(f"Instalando en: {install_path}")
        commands = [
            f"sudo cp {temp_file} {install_path}",
            f"sudo chmod +x {install_path}"
        ]
        
        for cmd in commands:
            result = system(cmd)
            if result != 0:
                console.print(f"\n[bold red]✗ Error al ejecutar: {cmd}[/bold red]")
                return False
        
        # Verificar instalación
        if path.exists(install_path):
            console.print("\n[bold green]✓ ManExplainer instalado correctamente[/bold green]")
            console.print("\nUso: manexplainer --command COMANDO --query PREGUNTA")
            console.print("\nEjemplos:")
            console.print("  manexplainer --command 'ls -la' --query 'Qué significan las columnas?'")
            console.print("  manexplainer --command grep --query 'Cómo busco en múltiples archivos?'")
            return True
        else:
            console.print("\n[bold red]✗ Error al instalar ManExplainer[/bold red]")
            return False
            
    except Exception as e:
        console.print(f"\n[bold red]✗ Error durante la instalación: {str(e)}[/bold red]")
        return False

async def send_request_with_gemini(prompt, max_retries=3, timeout_seconds=30):
    """Send request to Gemini AI model with timeout and retry logic"""
    retries = 0
    final_response = ""
    
    # Initialize Gemini client
    api_key = "YOUR_GEMINI_API_KEY"
    client = genai.Client(api_key=api_key)
    model = "gemini-2.0-flash-exp"
    config = {"response_modalities": ["TEXT"]}
    
    while retries < max_retries:
        try:
            if retries > 0:
                delayed_print(f"Reintentando solicitud ({retries}/{max_retries})...")
            
            final_response = ""
            request_failed = False
            request_done = False
            
            # Create an event for timeout control
            timeout_event = threading.Event()
            
            # Function to check timeout
            def check_timeout():
                sleep(timeout_seconds)
                if not timeout_event.is_set() and not request_done:
                    nonlocal request_failed
                    request_failed = True
                    delayed_print("\nTiempo de espera agotado. Cancelando solicitud...")
            
            # Start timeout thread
            timeout_thread = threading.Thread(target=check_timeout)
            timeout_thread.daemon = True
            timeout_thread.start()
            
            try:
                async with client.aio.live.connect(model=model, config=config) as session:
                    await session.send_client_content(
                        turns={"role": "user", "parts": [{"text": prompt}]}, turn_complete=True
                    )
                    
                    # Reset timeout on connection
                    timeout_event.set()
                    timeout_event.clear()
                    
                    if final_response == '':
                        clear_screen()
                    
                    async for response in session.receive():
                        if request_failed:
                            break
                            
                        if response.text is not None:
                            # Reset timeout on data received
                            timeout_event.set()
                            timeout_event.clear()
                            
                            print(response.text, end="", flush=True)
                            final_response += response.text
                    
                    request_done = True
                    timeout_event.set()
                
            except Exception as e:
                delayed_print(f"Error en la solicitud: {str(e)}")
                request_failed = True
            
            # If request completed successfully and we have a response, exit the loop
            if request_done and final_response:
                return final_response
                
            # If failed due to timeout or error, increment retry counter
            if request_failed or not final_response:
                retries += 1
                if retries >= max_retries:
                    delayed_print(f"Error después de {max_retries} intentos. No se pudo obtener respuesta.")
                    exit(1)
                delayed_print("Preparando nuevo intento en 2 segundos...")
                sleep(2)
                
        except Exception as e:
            delayed_print(f"Error inesperado: {str(e)}")
            retries += 1
            if retries >= max_retries:
                delayed_print(f"Error después de {max_retries} intentos.")
                exit(1)
            sleep(2)
    
    return final_response

def print_help():
    """Display help information"""
    clear_screen()
    console.print("[bold]ManExplainer[/bold] - Consulta documentación de comandos con IA\n")
    console.print("Uso:")
    console.print("  manexplainer --command COMANDO --query PREGUNTA")
    console.print("\nArgumentos:")
    console.print("  --command COMANDO  Comando de terminal para obtener su manual o ejecutar")
    console.print("  --query PREGUNTA   Pregunta que se le hará a la IA basada en el manual")
    console.print("\nEjemplos:")
    console.print("  manexplainer --command 'ls -la' --query 'Qué significan las columnas?'")
    console.print("  manexplainer --command grep --query 'Cómo busco en múltiples archivos?'")
    console.print("\nPara instalar:")
    console.print("  python3 manexplainer.py install")

async def main():
    # Check if running with "install" argument
    if len(argv) > 1 and argv[1] == "install":
        install_manexplainer()
        exit(0)
    
    # Check if no arguments were provided
    if len(argv) == 1:
        print_help()
        exit(0)
    
    start_time = time()
    clear_screen()
    delayed_print('Leyendo documentación...')

    # Argumentos CLI
    parser = ArgumentParser(description="Consulta documentación de comandos con IA.")
    parser.add_argument("--command", nargs=1, required=True, help="Comando de terminal para obtener su manual o ejecutar.")
    parser.add_argument("--query", nargs=1, required=True, help="Pregunta que se le hará a la IA basada en el manual.")
    
    try:
        args = parser.parse_args()
    except SystemExit:
        print_help()
        exit(1)

    # Validar que --query tenga un valor
    if len(args.query) != 1:
        print("Error: --query debe tener exactamente un valor.")
        exit(1)

    command = ''.join(args.command).split(' ')
    command_name = command[0]
    query = args.query[0]

    # Verificar si el comando tiene argumentos para ejecutarlo en lugar de usar man
    if len(command) > 1:
        delayed_print(f"Ejecutando comando: {' '.join(command)}")
        try:
            # Ejecutar el comando completo con sus argumentos
            cmd_output = check_output(command, stderr=STDOUT)
            cmd_text = cmd_output.decode('utf-8')
            
            # Armar prompt con la salida del comando + consulta
            prompt = f"""Tengo la siguiente salida del comando `{' '.join(command)}`:

{cmd_text}

Mi pregunta es: {query}
Por favor se conciso, muy técnico y resuelve mi duda usando la menor cantidad de tokens posible, se técnico también.
"""
        except CalledProcessError as e:
            print(f"Error ejecutando '{' '.join(command)}':\n{e.output.decode('utf-8')}")
            exit(1)
    else:
        # Obtener salida del comando man si solo hay un argumento
        delayed_print(f"Obteniendo manual para: {command_name}")
        try:
            man_output = check_output(['man', command_name], stderr=STDOUT)
            man_text = man_output.decode('utf-8')
            
            # Armar prompt con la documentación + consulta
            prompt = f"""Tengo el siguiente manual de Linux para el comando `{command_name}`:

{man_text}

Mi pregunta es: {query}
Por favor se conciso, muy técnico y resuelve mi duda usando la menor cantidad de tokens posible, se técnico también.
"""
        except CalledProcessError as e:
            print(f"Error ejecutando 'man {command_name}':\n{e.output.decode('utf-8')}")
            exit(1)

    clear_screen()
    delayed_print('Analizando tu pregunta...\n\n')

    # Enviar solicitud con manejo de timeout y reintentos
    final_response = await send_request_with_gemini(prompt)

    # Mostrar salida final con Markdown y encabezado
    clear_screen()
    console.print(Markdown(final_response))

    # Mostrar tiempo de ejecución
    elapsed = time() - start_time
    console.print(f"\n[bold green]⏱ Tiempo de respuesta:[/bold green] {elapsed:.2f} segundos\n")

if __name__ == '__main__':
    asyncio.run(main())