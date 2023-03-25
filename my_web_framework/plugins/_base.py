from my_web_framework.annotations import Annotation


class Plugin:
    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return False

    def do_something(self):
        print(f"Plugin is being called")