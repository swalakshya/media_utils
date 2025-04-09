import subprocess
import sys

def run_shell_command(cmd_arg_list, exit_on_failure=True, hide_output=True):
    if exit_on_failure:
        if hide_output:
            subprocess.check_call(cmd_arg_list, stdout=subprocess.PIPE, stderr=None)
            return True
        else:
            subprocess.check_call(cmd_arg_list)
    else:
        if hide_output:
            a = subprocess.run(cmd_arg_list, stdout=subprocess.PIPE, stderr=None)
            if a.returncode != 0:
                print(a.stdout)
                return False
            else:
                return True
        else:
            a = subprocess.run(cmd_arg_list)
            return a.returncode == 0


def run_shell_cmd_proc(cmd_arg_list, hide_output=True, exit_on_failure=True):
    so = None
    se = None
    print("Running command %s" % (cmd_arg_list))
    if hide_output:
        so = subprocess.PIPE
        se = subprocess.PIPE
    p = subprocess.Popen(cmd_arg_list, stdout=so, stderr=se)
    p.communicate()
    if p.returncode != 0 and exit_on_failure:
        print("Error running %s" % str(cmd_arg_list))
        if so is not None:
            print(se)
        sys.exit(1)
    return True
