import logging
import os
import bz2
import errno
import shutil
import logging
import hashlib
import subprocess
from enum import Enum
from pathlib import Path
from django.conf import settings
from abc import ABCMeta, abstractmethod
from diff_match_patch import diff_match_patch
from typing import Union
from bustime import dos2unix

logger = logging.getLogger(__name__)


class DBVer(Enum):
    v5 = 1
    v7 = 2


class DiffCmd(metaclass=ABCMeta):
    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def cleanup(self):
        pass

    @property
    def size(self):
        return 0


class GoogleDiffCmd(DiffCmd):

    def __init__(self, filename: str, data: bytes, data_path: Path, temp_path: Path) -> None:
        self.filename = filename
        self.data = data
        self.diff_hash = None
        self.data_path = data_path
        self.temp_path = temp_path

    def execute(self) -> (str, str):
        dmp = diff_match_patch()
        with open("{}/current/{}".format(self.data_path.as_posix(), self.filename.rstrip(".bz2")), 'rb') as file:
            text1 = self.data.decode('utf-8')
            text2 = file.read().decode('utf-8')
            diff = dmp.diff_main(text1, text2)
            if len(diff) > 2:
                dmp.diff_cleanupSemantic(diff)
            patch_list = dmp.patch_make(text1, text2, diff)
            patch_text = dmp.patch_toText(patch_list).encode('utf-8')
            self.diff_hash = hashlib.md5(patch_text).hexdigest()
            with bz2.BZ2File("{}/{}".format(self.temp_path.as_posix(), self.diff_hash), 'wb') as f:
                f.write(patch_text)
            return patch_text, self.diff_hash

    def cleanup(self) -> None:
        diff_file_path = self.temp_path / self.diff_hash
        try:
            os.remove(diff_file_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    @property
    def size(self):
        return len(self.data)


class PosixDiffCmd(DiffCmd):

    def __init__(self, filename: str, data: bytes, data_path: Path, temp_path: Path) -> None:
        self.data_hash = hashlib.md5(data).hexdigest()
        self.filename = filename
        self.data = data
        self.diff_hash = None
        self.data_path = data_path
        self.temp_path = temp_path
        with open("{}/{}".format(temp_path.as_posix(), self.data_hash), "wb") as f:
            f.write(data)

    def execute(self) -> (bytes, str):
        result = subprocess.run(
            ["/usr/bin/diff",
             "{}/{}".format(self.temp_path.as_posix(), self.data_hash),
             "{}/current/{}".format(self.data_path.as_posix(), self.filename)],
            stdout=subprocess.PIPE)
        # result_diff = result.stdout.replace(b'\r\n', b'\n').replace(b'\r', b'')
        result_diff = dos2unix.dos2unix(result.stdout).read()
        self.diff_hash = hashlib.md5(result_diff).hexdigest()
        with bz2.BZ2File("{}/{}".format(self.temp_path.as_posix(), self.diff_hash), 'wb') as f:
            f.write(result_diff)
        logger.debug(result_diff.decode('utf-8'))
        return result_diff, self.diff_hash

    def cleanup(self) -> None:
        diff_file_path = self.temp_path / self.diff_hash
        data_file_path = self.temp_path / self.data_hash
        try:
            os.remove(diff_file_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        try:
            os.remove(data_file_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    @property
    def size(self):
        return len(self.data)


class DiffProcessor(object):

    def __init__(self, db_ver: DBVer) -> None:
        self.db_ver = db_ver
        self.data_path = Path(settings.PROJECT_DIR) / "bustime" / "static" / "other" / "db" / db_ver.name
        self.temp_path = Path("/tmp/bustime_mobile_dumps") / db_ver.name
        self.static_path = Path(settings.PROJECT_DIR) / "static" / "other" / "db" / db_ver.name
        self.temp_path.mkdir(parents=True, exist_ok=True)

    def _try_renew_dump(self, filepath: Path, diff_cmd: DiffCmd, diff: Union[str, bytes]):
        if len(diff) > diff_cmd.size * 0.2:
            logger.info("replacing old dump {}".format(filepath.name.rstrip(".bz2")))
            curr_dump_path = self.data_path / "current" / filepath.name.rstrip(".bz2")
            # subprocess.run(["/usr/bin/dos2unix", curr_dump_path])
            with bz2.BZ2File(filepath, "wb") as bz2_dump, open(curr_dump_path, "rb") as f:
                data = f.read()
                bz2_dump.write(dos2unix.dos2unix(data).read())
                # bz2_dump.write(data.replace(b'\r\n', b'\n').replace(b'\r', b''))
                subprocess.run(["/bin/ln", "-sfn", filepath.as_posix(), self.static_path.as_posix()])
                return True
        return False

    def _try_renew_diff(self, filepath: Path, diff: Union[str, bytes], diff_hash: str, diff_ext: str = "diff"):
        if len(diff) > 0:
            result_cmp = subprocess.run(
                ["/usr/bin/cmp",
                 self.temp_path / diff_hash,
                 Path(filepath.as_posix().replace(".dump.bz2", f".dump.{diff_ext}.bz2"))],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.debug(result_cmp.stdout.decode('utf-8'))
            if len(result_cmp.stderr) > 0:
                logger.warning(result_cmp.stderr.decode('utf-8'))
            if len(result_cmp.stdout) > 0 or len(result_cmp.stderr) > 0:
                logger.info("{} diff! [overwrite {}]".format(filepath.name,
                                                             filepath.name.replace(".dump.bz2", f".dump.{diff_ext}.bz2")))
                new_dump_path = Path(filepath.as_posix().replace(".dump.bz2", f".dump.{diff_ext}.bz2"))
                shutil.copyfile(Path(self.temp_path / diff_hash), new_dump_path)
                subprocess.run(["/bin/ln", "-sfn", new_dump_path.as_posix(), self.static_path.as_posix()])
                # new_dump_path.symlink_to(static_path, True)
                return True
        return False

    def _posix_diff_one(self, filename: Path) -> bool:
        update_finished = False
        if filename.match("*.dump.bz2"):
            with bz2.BZ2File("{}".format(filename), "rb") as bz2_dump:
                diff_cmd = PosixDiffCmd(filename.name.rstrip(".bz2"), bz2_dump.read(), self.data_path, self.temp_path)
                result_diff, diff_hash = diff_cmd.execute()
            if self._try_renew_dump(filename, diff_cmd, result_diff):
                DiffProcessor.remove_diffs(filename)
                update_finished = True
            elif not self._try_renew_diff(filename, result_diff, diff_hash):
                logger.info("Posix Diff: {} dump changes not found {}".format(self.db_ver.name, filename.name))
            diff_cmd.cleanup()
        return update_finished

    def _google_diff_one(self, filename: Path) -> bool:
        update_finished = False
        if filename.match("*.dump.bz2"):
            with bz2.BZ2File("{}".format(filename), "rb") as bz2_dump:
                diff_cmd = GoogleDiffCmd(filename.name.rstrip(".bz2"), bz2_dump.read(), self.data_path, self.temp_path)
                result_diff, diff_hash = diff_cmd.execute()
            if self._try_renew_dump(filename, diff_cmd, result_diff):
                DiffProcessor.remove_diffs(filename)
                update_finished = True
            elif not self._try_renew_diff(filename, result_diff, diff_hash, diff_ext="diff.patch"):
                logger.info("Google Diff: {} dump changes not found {}".format(self.db_ver.name, filename.name))
            diff_cmd.cleanup()
        return update_finished

    def copy_skipped(self):
        db_curr_path = Path("{}/current".format(self.data_path))
        for filename in db_curr_path.iterdir():
            if filename.match("*.dump"):
                # subprocess.run(["/usr/bin/dos2unix", "{}/{}".format(self.temp_path.as_posix(), filename.name)])
                filepath = "{}/{}.bz2".format(self.data_path.as_posix(), filename.name)
                if not os.path.isfile(filepath):
                    logger.info(filepath)
                    with bz2.BZ2File(filepath, "wb") as bz2_dump:
                        bz2_dump.write(dos2unix.dos2unix(filename.read_bytes()).read())
                        # bz2_dump.write(filename.read_bytes().replace(b'\r\n', b'\n').replace(b'\r', b''))

    def copy_skipped_one(self, city_id: int):
        db_curr_path = Path("{}/current/{}.dump".format(self.data_path, city_id))
        filepath = "{}/{}.dump.bz2".format(self.data_path.as_posix(), city_id)
        # subprocess.run(["/usr/bin/dos2unix", "{}/{}".format(self.temp_path.as_posix(), filepath)])
        if not os.path.isfile(filepath):
            logger.info(filepath)
            with bz2.BZ2File(filepath, "wb") as bz2_dump:
                bz2_dump.write(dos2unix.dos2unix(db_curr_path.read_bytes()).read())
                # bz2_dump.write(db_curr_path.read_bytes().replace(b'\r\n', b'\n').replace(b'\r', b''))

    def diff_all(self):
        self.copy_skipped()
        for filename in self.data_path.iterdir():
            if not self._posix_diff_one(filename):
                self._google_diff_one(filename)

    def diff_all_google(self):
        for filename in self.data_path.iterdir():
            self._google_diff_one(filename)

    def diff_one(self, city_id: int):
        self.copy_skipped_one(city_id)
        filepath = self.data_path / "{}.dump.bz2".format(city_id)
        if not self._posix_diff_one(filepath):
            self._google_diff_one(filepath)

    def diff_one_google(self, city_id: int):
        self.copy_skipped_one(city_id)
        filepath = self.data_path / "{}.dump.bz2".format(city_id)
        self._google_diff_one(filepath)

    def google_patch_apply(self, city_id: int):
        filepath = self.data_path / "{}.dump.bz2".format(city_id)
        dmp = diff_match_patch()
        with bz2.BZ2File(filepath, 'rb') as bz2_file, bz2.BZ2File(
                "{}/{}".format(self.data_path.as_posix(), filepath.name.replace(".bz2", ".diff.patch.bz2"))) as bz2_diff:
            text1 = bz2_file.read().decode('utf-8')
            patch_text = bz2_diff.read().decode('utf-8')
            patches = dmp.patch_fromText(patch_text)
            results = dmp.patch_apply(patches, text1)
            logger.info(results)

    @staticmethod
    def remove_diffs(filepath: Path):
        diff_path = filepath.parent / filepath.name.replace(".bz2", ".diff.bz2")
        patch_path = filepath.parent / filepath.name.replace(".bz2", ".diff.patch.bz2")
        try:
            os.remove(diff_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        try:
            os.remove(patch_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
