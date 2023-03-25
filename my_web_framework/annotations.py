class Annotation:
    pass


def add_annotation(f, annotation: Annotation) -> None:
    annotations = getattr(f, "_annotations", [])
    annotations.append(annotation)
    setattr(f, "_annotations", annotations)
