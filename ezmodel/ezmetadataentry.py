from dataclasses import dataclass
from dataclasses_json import dataclass_json
from enum import Enum

@dataclass_json
@dataclass
class EzMetadataEntry:
    """Imports a stack of image files from a directory into a 3D Zarr volume.

    Parameters
    ----------

    """

    class SourceType(Enum):
        FILE = 1
        CUSTOM = 2

    unique_id: int = 0
    parent: int = -1
    children: List[int] = field(default_factory= list)
    
    source_path: str = ""
    source_value: str = ""
    ht_name: str = ""
    ht_value: str = ""
    ht_annotation: str = ""
    ht_units: str = ""
    source_type: SourceType = SourceType.FILE
    override_source_value: bool = False
    editable: bool = True
    required: bool = False
    enabled: bool = True


