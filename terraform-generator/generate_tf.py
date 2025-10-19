import yaml
from jinja2 import Environment, FileSystemLoader
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, ".out")
os.makedirs(OUT_DIR, exist_ok=True)


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)

def render_template(template_name, context, output_name):
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(template_name)
    rendered = template.render(context)
    with open(output_name, "w") as f:
        f.write(rendered)

if __name__ == "__main__":
    config = load_config()
    modules = [
        ("locals.tf.j2", "locals.tf"),
        ("s3.tf.j2", "s3.tf"),
        ("lambda.tf.j2", "lambda.tf"),
        ("apigateway.tf.j2", "apigateway.tf"),
        ("cloudfront.tf.j2", "cloudfront.tf"),
        ("route53.tf.j2", "route53.tf")
    ]
    for template_name, output_name in modules:
     render_template(template_name, config, f".out/{output_name}")
    render_template("azure_vm.tf.j2", config, "azure.tf")
