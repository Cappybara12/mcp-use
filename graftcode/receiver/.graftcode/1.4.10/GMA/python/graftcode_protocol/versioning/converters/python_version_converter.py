"""
Converts between Python (PEP 440) version strings and the canonical PackageVersion format.
"""
import re
from .base_version_converter import BaseVersionConverter
from ...models.package_version import PackageVersion


class PythonVersionConverter(BaseVersionConverter):
    """
    Converts between Python (PEP 440) version strings and the canonical PackageVersion format.
    
    Supports:
    - Basic: 1.0.0
    - Epochs: 1!2.0.0
    - Pre-releases: 1.0.0a1, 1.0.0.alpha.1, 1.0.0b2, 1.0.0rc3
    - Post-releases: 1.0.0.post1
    - Dev releases: 1.0.0.dev1
    - Combined: 1.0.0.post1.dev1
    - Local versions: 1.0.0+ubuntu1
    """

    # Enhanced PEP 440 pattern supporting all cases
    # Format: [epoch!]major.minor.patch[prerelease][.postN][.devN][+local]
    VERSION_PATTERN = re.compile(
        r'^(?:(?P<epoch>\d+)!)?'
        r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'
        r'(?:\.?(?P<prerelease>a|alpha|b|beta|rc)\.?(?P<number>\d+))?'
        r'(?:\.?(?P<post>post)\.?(?P<postnumber>\d+))?'
        r'(?:\.?(?P<dev>dev)\.?(?P<devnumber>\d+))?'
        r'(?:\+(?P<local>[a-zA-Z0-9.]+))?$',
        re.IGNORECASE
    )

    # Note: We preserve the original label format in canonical representation
    # "a" stays "a", "alpha" stays "alpha", "b" stays "b", "beta" stays "beta"

    CANONICAL_TO_PYTHON: dict[str, str] = {
        'a': 'a',
        'alpha': 'a',
        'b': 'b',
        'beta': 'b',
        'rc': 'rc',
        'dev': 'dev',
        'post': 'post',
    }

    def to_canonical(self, version_string: str) -> PackageVersion:
        """
        Converts a Python version string to the canonical PackageVersion format.
        Supports formats: 1.2.3, 1.2.3a1, 1.2.3.a.1, 1.2.3b2, 1.2.3rc3, 1.2.3.dev1, 1.2.3.post1

        Raises:
            ValueError: If version_string is empty or does not match PEP 440.
        """
        if not version_string or not version_string.strip():
            raise ValueError("Version string cannot be null or empty.")

        version_string = version_string.strip()
        match = self.VERSION_PATTERN.match(version_string)
        if not match:
            raise ValueError(
                f"Version string '{version_string}' does not match Python PEP 440 format."
            )

        epoch = int(match.group('epoch')) if match.group('epoch') else None
        major = int(match.group('major'))
        minor = int(match.group('minor'))
        patch = int(match.group('patch'))

        prerelease_label = None
        prerelease_number = None
        build_metadata = None
        local_version = None

        if match.group('prerelease'):
            prerelease_label = match.group('prerelease').lower()
            if match.group('number'):
                prerelease_number = int(match.group('number'))

        has_dev = match.group('dev')
        has_post = match.group('post')

        if has_dev and not has_post and not prerelease_label:
            prerelease_label = 'dev'
            if match.group('devnumber'):
                prerelease_number = int(match.group('devnumber'))
        else:
            build_parts = []
            if has_post:
                post_number = match.group('postnumber')
                build_parts.append(f"post.{post_number}" if post_number else "post")
            if has_dev and (has_post or prerelease_label):
                dev_number = match.group('devnumber')
                build_parts.append(f"dev.{dev_number}" if dev_number else "dev")
            if build_parts:
                build_metadata = ".".join(build_parts)

        if match.group('local'):
            local_version = match.group('local')

        return PackageVersion(
            major, minor, patch,
            prerelease_label, prerelease_number, build_metadata,
            epoch, local_version
        )

    def from_canonical(self, canonical: PackageVersion) -> str:
        """
        Converts a canonical PackageVersion to a Python version string.
        Produces format: 1.2.3 or 1.2.3a1 or 1.2.3b2 or 1.2.3rc3 or 1.2.3.dev1 (compact form without dots)
        Post releases stored in build_metadata (e.g., "post.1") are converted back to .post1 format
        """
        if canonical is None:
            raise ValueError("Canonical version cannot be None.")

        version = ""
        
        # Add epoch if present
        if canonical.epoch is not None:
            version += f"{canonical.epoch}!"
        
        version += f"{canonical.major}.{canonical.minor}.{canonical.patch}"

        if canonical.prerelease_label:
            label = canonical.prerelease_label.lower()
            # dev releases use dot notation, others don't
            if label == 'dev':
                version += f".{label}"
            else:
                version += label

            if canonical.prerelease_number is not None:
                version += str(canonical.prerelease_number)

        # Handle post and dev releases from build metadata
        if canonical.build_metadata:
            parts = canonical.build_metadata.split('.')
            i = 0
            while i < len(parts):
                if parts[i] == 'post' and i + 1 < len(parts):
                    version += f".post{parts[i + 1]}"
                    i += 2
                elif parts[i] == 'post':
                    version += ".post"
                    i += 1
                elif parts[i] == 'dev' and i + 1 < len(parts):
                    version += f".dev{parts[i + 1]}"
                    i += 2
                elif parts[i] == 'dev':
                    version += ".dev"
                    i += 1
                else:
                    i += 1
        
        # Add local version if present
        if canonical.local_version:
            version += f"+{canonical.local_version}"

        return version

    @staticmethod
    def from_canonical_dotted(canonical: PackageVersion) -> str:
        """
        Converts a canonical PackageVersion to a Python version string with dot-separated prerelease.
        Produces format: 1.2.3 or 1.2.3.a.1 or 1.2.3.b.2 or 1.2.3.rc.3 (dotted form)
        Note: This is an alternative format; use from_canonical for the standard compact format.
        """
        if canonical is None:
            raise ValueError("Canonical version cannot be None.")

        version = f"{canonical.major}.{canonical.minor}.{canonical.patch}"

        if canonical.prerelease_label:
            # Convert canonical label to Python label
            python_label = PythonVersionConverter.CANONICAL_TO_PYTHON.get(
                canonical.prerelease_label.lower(),
                canonical.prerelease_label
            )

            version += f".{python_label}"

            if canonical.prerelease_number is not None:
                version += f".{canonical.prerelease_number}"

        return version
