/*
 * Launch a python module from an archive.
 * Copyright (C) 2005-2011, Giovanni Bajo
 * Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * In addition to the permissions in the GNU General Public License, the
 * authors give you unlimited permission to link or embed the compiled
 * version of this file into combinations with other programs, and to
 * distribute those combinations without any restriction coming from the
 * use of this file. (The General Public License restrictions do apply in
 * other respects; for example, they cover modification of the file, and
 * distribution when not linked into a combine executable.)
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
 */
#include <stdio.h>
#ifdef WIN32
 #include <windows.h>
 #include <direct.h>
 #include <process.h>
 #include <io.h>
#else
 #include <unistd.h>
 #include <fcntl.h>
 #include <dlfcn.h>
 #include <dirent.h>
 #include <stdarg.h>
#endif
#include <sys/types.h>
#include <sys/stat.h>
#include "launch.h"
#include <string.h>
#include "zlib.h"

#include "pyi_global.h"
#include "pyi_utils.h"

#ifdef WIN32
#define snprintf _snprintf
#define vsnprintf _vsnprintf
#endif

/*
 * Python Entry point declarations (see macros in launch.h).
 */
DECLVAR(Py_FrozenFlag);
DECLVAR(Py_NoSiteFlag);
DECLVAR(Py_OptimizeFlag);
DECLVAR(Py_VerboseFlag);
DECLPROC(Py_Initialize);
DECLPROC(Py_Finalize);
DECLPROC(Py_IncRef);
DECLPROC(Py_DecRef);
DECLPROC(Py_SetPythonHome);
DECLPROC(PyImport_ExecCodeModule);
DECLPROC(PyRun_SimpleString);
DECLPROC(PySys_SetArgv);
DECLPROC(Py_SetProgramName);
DECLPROC(PyImport_ImportModule);
DECLPROC(PyImport_AddModule);
DECLPROC(PyObject_SetAttrString);
DECLPROC(PyList_New);
DECLPROC(PyList_Append);
DECLPROC(Py_BuildValue);
DECLPROC(PyString_FromStringAndSize);
DECLPROC(PyFile_FromString);
DECLPROC(PyString_AsString);
DECLPROC(PyObject_CallFunction);
DECLPROC(PyModule_GetDict);
DECLPROC(PyDict_GetItemString);
DECLPROC(PyErr_Clear);
DECLPROC(PyErr_Occurred);
DECLPROC(PyErr_Print);
DECLPROC(PyObject_CallObject);
DECLPROC(PyObject_CallMethod);
DECLPROC(PySys_AddWarnOption);
DECLPROC(PyEval_InitThreads);
DECLPROC(PyEval_AcquireThread);
DECLPROC(PyEval_ReleaseThread);
DECLPROC(PyThreadState_Swap);
DECLPROC(Py_NewInterpreter);
DECLPROC(Py_EndInterpreter);
DECLPROC(PyInt_AsLong);
DECLPROC(PySys_SetObject);


unsigned char *extract(ARCHIVE_STATUS *status, TOC *ptoc);

/*
 * The functions in this file defined in reverse order so that forward
 * declarations are not necessary.
 */


#if defined(WIN32) && defined(WINDOWED)
/* The code duplication in the functions below are because
 * standard macros with variable numer of arguments (variadic macros) are
 * supported by Microsoft only starting from Visual C++ 2005.
 */

#define MBTXTLEN 200

void mbfatalerror(const char *fmt, ...)
{
	char msg[MBTXTLEN];
	va_list args;

	va_start(args, fmt);
	vsnprintf(msg, MBTXTLEN, fmt, args);
	msg[MBTXTLEN-1] = '\0';
	va_end(args);

	MessageBox(NULL, msg, "Fatal Error!", MB_OK | MB_ICONEXCLAMATION);
}

void mbothererror(const char *fmt, ...)
{
	char msg[MBTXTLEN];
	va_list args;

	va_start(args, fmt);
	vsnprintf(msg, MBTXTLEN, fmt, args);
	msg[MBTXTLEN-1] = '\0';
	va_end(args);

	MessageBox(NULL, msg, "Error!", MB_OK | MB_ICONWARNING);
}

void mbvs(const char *fmt, ...)
{
	char msg[MBTXTLEN];
	va_list args;

	va_start(args, fmt);
	vsnprintf(msg, MBTXTLEN, fmt, args);
	msg[MBTXTLEN-1] = '\0';
	va_end(args);

	MessageBox(NULL, msg, "Tracing", MB_OK);
}

#endif /* WIN32 and WINDOWED */


static int checkFile(char *buf, const char *fmt, ...)
{
    va_list args;
    struct stat tmp;

    va_start(args, fmt);
    vsnprintf(buf, PATH_MAX, fmt, args);
    va_end(args);

    return stat(buf, &tmp);
}

/*
 * Set up paths required by rest of this module
 * Sets f_archivename, f_homepath
 */
int pyi_arch_set_paths(ARCHIVE_STATUS *status, char const * archivePath, char const * archiveName)
{
#ifdef WIN32
	char *p;
#endif
	/* Get the archive Path */
	strcpy(status->archivename, archivePath);
	strcat(status->archivename, archiveName);

	/* Set homepath to where the archive is */
	strcpy(status->homepath, archivePath);
#ifdef WIN32
    /* Replace backslashes with forward slashes. */
    // TODO eliminate the need for this conversion and homepathraw and temppathraw
	strcpy(status->homepathraw, archivePath);
	for ( p = status->homepath; *p; p++ )
		if (*p == '\\')
			*p = '/';
#endif

    /*
     * Initial value of mainpath is homepath. It might be overriden
     * by temppath if it is available.
     */
    status->has_temp_directory = false;
#ifdef WIN32
	strcpy(status->mainpath, status->homepathraw);
#else
	strcpy(status->mainpath, status->homepath);
#endif

	return 0;
}

int pyi_arch_check_cookie(ARCHIVE_STATUS *status, int filelen)
{
	if (fseek(status->fp, filelen-(int)sizeof(COOKIE), SEEK_SET))
		return -1;

	/* Read the Cookie, and check its MAGIC bytes */
	if (fread(&(status->cookie), sizeof(COOKIE), 1, status->fp) < 1)
	    return -1;
	if (strncmp(status->cookie.magic, MAGIC, strlen(MAGIC)))
		return -1;

  return 0;
}

int findDigitalSignature(ARCHIVE_STATUS * const status)
{
#ifdef WIN32
	/* There might be a digital signature attached. Let's see. */
	char buf[2];
	int offset = 0, signature_offset = 0;
	fseek(status->fp, 0, SEEK_SET);
	fread(buf, 1, 2, status->fp);
	if (!(buf[0] == 'M' && buf[1] == 'Z'))
		return -1;
	/* Skip MSDOS header */
	fseek(status->fp, 60, SEEK_SET);
	/* Read offset to PE header */
	fread(&offset, 4, 1, status->fp);
	fseek(status->fp, offset+24, SEEK_SET);
        fread(buf, 2, 1, status->fp);
        if (buf[0] == 0x0b && buf[1] == 0x01) {
          /* 32 bit binary */
          signature_offset = 152;
        }
        else if (buf[0] == 0x0b && buf[1] == 0x02) {
          /* 64 bit binary */
          signature_offset = 168;
        }
        else {
          /* Invalid magic value */
          VS("Could not find a valid magic value (was %x %x).\n", (unsigned int) buf[0], (unsigned int) buf[1]);
          return -1;
        }

	/* Jump to the fields that contain digital signature info */
	fseek(status->fp, offset+signature_offset, SEEK_SET);
	fread(&offset, 4, 1, status->fp);
	if (offset == 0)
		return -1;
  VS("%s contains a digital signature\n", status->archivename);
	return offset;
#else
	return -1;
#endif
}

/*
 * Open the archive
 * Sets f_archiveFile, f_pkgstart, f_tocbuff and f_cookie.
 */
int pyi_arch_open(ARCHIVE_STATUS *status)
{
#ifdef WIN32
	int i;
#endif
	int filelen;
    VS("archivename is %s\n", status->archivename);
	/* Physically open the file */
	status->fp = fopen(status->archivename, "rb");
	if (status->fp == NULL) {
		VS("Cannot open archive: %s\n", status->archivename);
		return -1;
	}

	/* Seek to the Cookie at the end of the file. */
	fseek(status->fp, 0, SEEK_END);
	filelen = ftell(status->fp);

	if (pyi_arch_check_cookie(status, filelen) < 0)
	{
		VS("%s does not contain an embedded package\n", status->archivename);
#ifndef WIN32
    return -1;
#else
		filelen = findDigitalSignature(status);
		if (filelen < 1)
			return -1;
		/* The digital signature has been aligned to 8-bytes boundary.
		   We need to look for our cookie taking into account some
		   padding. */
		for (i = 0; i < 8; ++i)
		{
			if (pyi_arch_check_cookie(status, filelen) >= 0)
				break;
			--filelen;
		}
		if (i == 8)
		{
			VS("%s does not contain an embedded package, even skipping the signature\n", status->archivename);
			return -1;
		}
		VS("package found skipping digital signature in %s\n", status->archivename);
#endif
	}

	/* From the cookie, calculate the archive start */
	status->pkgstart = filelen - ntohl(status->cookie.len);

	/* Read in in the table of contents */
	fseek(status->fp, status->pkgstart + ntohl(status->cookie.TOC), SEEK_SET);
	status->tocbuff = (TOC *) malloc(ntohl(status->cookie.TOClen));
	if (status->tocbuff == NULL)
	{
		FATALERROR("Could not allocate buffer for TOC.");
		return -1;
	}
	if (fread(status->tocbuff, ntohl(status->cookie.TOClen), 1, status->fp) < 1)
	{
	    FATALERROR("Could not read from file.");
	    return -1;
	}
	status->tocend = (TOC *) (((char *)status->tocbuff) + ntohl(status->cookie.TOClen));

	/* Check input file is still ok (should be). */
	if (ferror(status->fp))
	{
		FATALERROR("Error on file");
		return -1;
	}
	return 0;
}
int mapNames(HMODULE dll, int pyvers)
{
    /* Get all of the entry points that we are interested in */
    GETVAR(dll, Py_FrozenFlag);
    GETVAR(dll, Py_NoSiteFlag);
    GETVAR(dll, Py_OptimizeFlag);
    GETVAR(dll, Py_VerboseFlag);
    GETPROC(dll, Py_Initialize);
    GETPROC(dll, Py_Finalize);
    GETPROCOPT(dll, Py_IncRef);
    GETPROCOPT(dll, Py_DecRef);
    GETPROC(dll, Py_SetPythonHome);
    GETPROC(dll, PyImport_ExecCodeModule);
    GETPROC(dll, PyRun_SimpleString);
    GETPROC(dll, PyString_FromStringAndSize);
    GETPROC(dll, PySys_SetArgv);
    GETPROC(dll, Py_SetProgramName);
    GETPROC(dll, PyImport_ImportModule);
    GETPROC(dll, PyImport_AddModule);
    GETPROC(dll, PyObject_SetAttrString);
    GETPROC(dll, PyList_New);
    GETPROC(dll, PyList_Append);
    GETPROC(dll, Py_BuildValue);
    GETPROC(dll, PyFile_FromString);
    GETPROC(dll, PyString_AsString);
    GETPROC(dll, PyObject_CallFunction);
    GETPROC(dll, PyModule_GetDict);
    GETPROC(dll, PyDict_GetItemString);
    GETPROC(dll, PyErr_Clear);
    GETPROC(dll, PyErr_Occurred);
    GETPROC(dll, PyErr_Print);
    GETPROC(dll, PyObject_CallObject);
    GETPROC(dll, PyObject_CallMethod);
    GETPROC(dll, PySys_AddWarnOption);
    GETPROC(dll, PyEval_InitThreads);
    GETPROC(dll, PyEval_AcquireThread);
    GETPROC(dll, PyEval_ReleaseThread);
    GETPROC(dll, PyThreadState_Swap);
    GETPROC(dll, Py_NewInterpreter);
    GETPROC(dll, Py_EndInterpreter);
    GETPROC(dll, PyInt_AsLong);
    GETPROC(dll, PySys_SetObject);

    return 0;
}

/*
 * Load the Python DLL, and get all of the necessary entry points
 */
int pyi_pylib_load(ARCHIVE_STATUS *status)
{
	dylib_t dll;
	char dllpath[PATH_MAX + 1];
    char dllname[64];
    int pyvers = ntohl(status->cookie.pyvers);

#ifdef AIX
    /*
     * On AIX 'ar' archives are used for both static and shared object.
     * To load a shared object from a library, it should be loaded like this:
     *   dlopen("libpython2.6.a(libpython2.6.so)", RTLD_MEMBER)
     */
    uint32_t pyvers_major;
    uint32_t pyvers_minor;
#endif

    strcpy(dllname, status->cookie.pylibname);

    /*
     * Look for Python library in homepath or temppath.
     * It depends on the value of mainpath.
     */
    strcpy(dllpath, status->mainpath);

#ifdef AIX
    pyvers_major = pyvers / 10;
    pyvers_minor = pyvers % 10;

    /* Append the shared object member to the library path
     * to make it look like this:
     *   libpython2.6.a(libpython2.6.so)
     */
    sprintf(dllpath + strlen(dllpath), "(libpython%01d.%01d.so)", pyvers_major, pyvers_minor);
#endif

    /* Append Python library name to dllpath. */
    strcat(dllpath, dllname);
    VS("Python library: %s\n", dllpath);

	/* Load the DLL */
    dll = pyi_dlopen(dllpath);

    /* Check success of loading Python library. */
	if (dll == 0) {
#ifdef WIN32
		FATALERROR("Error loading Python DLL: %s (error code %d)\n",
			dllpath, GetLastError());
#else
		FATALERROR("Error loading Python lib '%s': %s\n",
			dllpath, dlerror());
#endif
		return -1;
	}

	mapNames(dll, pyvers);
	return 0;
}

/*
 * use this from a dll instead of pyi_pylib_load()
 * it will attach to an existing pythonXX.dll,
 * or load one if needed.
 */
int pyi_pylib_attach(ARCHIVE_STATUS *status, int *loadedNew)
{
#ifdef WIN32
	HMODULE dll;
	char nm[PATH_MAX + 1];
    int pyvers = ntohl(status->cookie.pyvers);

	/* Get python's name */
	sprintf(nm, "python%02d.dll", pyvers);

	/* See if it's loaded */
	dll = GetModuleHandleA(nm);
	if (dll == 0) {
		*loadedNew = 1;
		return pyi_pylib_load(status);
	}
	mapNames(dll, pyvers);
	*loadedNew = 0;
#endif
	return 0;
}

/*
 * Return pointer to next toc entry.
 */
TOC *incrementTocPtr(ARCHIVE_STATUS *status, TOC* ptoc)
{
	TOC *result = (TOC*)((char *)ptoc + ntohl(ptoc->structlen));
	if (result < status->tocbuff) {
		FATALERROR("Cannot read Table of Contents.\n");
		return status->tocend;
	}
	return result;
}
/*
 * external API for iterating TOCs
 */
TOC *getFirstTocEntry(ARCHIVE_STATUS *status)
{
	return status->tocbuff;
}
TOC *getNextTocEntry(ARCHIVE_STATUS *status, TOC *entry)
{
	TOC *rslt = (TOC*)((char *)entry + ntohl(entry->structlen));
	if (rslt >= status->tocend)
		return NULL;
	return rslt;
}
/*
 * A toc entry of type 'o' holds runtime options
 * toc->name is the arg
 * this is so you can freeze in command line args to Python
 */
int setRuntimeOptions(ARCHIVE_STATUS *status)
{
	int unbuffered = 0;
	TOC *ptoc = status->tocbuff;
	while (ptoc < status->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_RUNTIME_OPTION) {
			VS("%s\n", ptoc->name);
			switch (ptoc->name[0]) {
			case 'v':
				*PI_Py_VerboseFlag = 1;
			break;
			case 'u':
				unbuffered = 1;
			break;
			case 'W':
                                PI_PySys_AddWarnOption(&ptoc->name[2]);
			break;
			case 's':
				*PI_Py_NoSiteFlag = 0;
			break;
			case 'O':
				*PI_Py_OptimizeFlag = 1;
			break;
			}
		}
		ptoc = incrementTocPtr(status, ptoc);
	}
	if (unbuffered) {
#ifdef WIN32
		_setmode(fileno(stdin), O_BINARY);
		_setmode(fileno(stdout), O_BINARY);
#else
		fflush(stdout);
		fflush(stderr);

		setbuf(stdin, (char *)NULL);
		setbuf(stdout, (char *)NULL);
		setbuf(stderr, (char *)NULL);
#endif
	}
	return 0;
}
/*
 * Start python - return 0 on success
 */
int pyi_pylib_start_python(ARCHIVE_STATUS *status, int argc, char *argv[])
{
    /* Set PYTHONPATH so dynamic libs will load.
     * PYTHONHOME for function Py_SetPythonHome() should point
     * to a zero-terminated character string in static storage. */
	static char pypath[2*PATH_MAX + 14];
	int pathlen = 1;
	int i;
	char cmd[PATH_MAX+1+80];
	char tmp[PATH_MAX+1];
	PyObject *py_argv;
	PyObject *val;
	PyObject *sys;

    /* Set the PYTHONPATH */
	VS("Manipulating evironment\n");
    strcpy(pypath, status->mainpath);
	/* don't chop off SEP if root directory */
#ifdef WIN32
	if (strlen(pypath) > 14)
#else
	if (strlen(pypath) > 12)
#endif
		pypath[strlen(pypath)-1] = '\0';

	pyi_setenv("PYTHONPATH", pypath);
	VS("PYTHONPATH=%s\n", pypath);


	/* Clear out PYTHONHOME to avoid clashing with any Python installation. */
	pyi_unsetenv("PYTHONHOME");

    /* Set PYTHONHOME by using function from Python C API. */
    strcpy(pypath, status->mainpath);
    /* On Windows remove back slash '\\' from the end. */
    // TODO remove this hook when path handling is fixed in bootloader.
    #ifdef WIN32
    /* Remove trailing slash in directory path. */
    pypath[strlen(pypath)-1] = '\0';
    #endif
    PI_Py_SetPythonHome(pypath);
	VS("PYTHONHOME=%s\n", pypath);


	/* Start python. */
	/* VS("Loading python\n"); */
	*PI_Py_NoSiteFlag = 1;	/* maybe changed to 0 by setRuntimeOptions() */
    *PI_Py_FrozenFlag = 1;
	setRuntimeOptions(status);
	PI_Py_SetProgramName(status->archivename); /*XXX*/
	PI_Py_Initialize();

	/* Set sys.path */
	/* VS("Manipulating Python's sys.path\n"); */
	PI_PyRun_SimpleString("import sys\n");
	PI_PyRun_SimpleString("del sys.path[:]\n");
    if (status->temppath[0] != '\0') {
        strcpy(tmp, status->temppath);
	    tmp[strlen(tmp)-1] = '\0';
	    sprintf(cmd, "sys.path.append(r\"%s\")", tmp);
        PI_PyRun_SimpleString(cmd);
    }

	strcpy(tmp, status->homepath);
	tmp[strlen(tmp)-1] = '\0';
	sprintf(cmd, "sys.path.append(r\"%s\")", tmp);
	PI_PyRun_SimpleString (cmd);

	/* Set argv[0] to be the archiveName */
	py_argv = PI_PyList_New(0);
	val = PI_Py_BuildValue("s", status->archivename);
	PI_PyList_Append(py_argv, val);
	for (i = 1; i < argc; ++i) {
		val = PI_Py_BuildValue ("s", argv[i]);
		PI_PyList_Append (py_argv, val);
	}
	sys = PI_PyImport_ImportModule("sys");
	/* VS("Setting sys.argv\n"); */
	PI_PyObject_SetAttrString(sys, "argv", py_argv);

	/* Check for a python error */
	if (PI_PyErr_Occurred())
	{
		FATALERROR("Error detected starting Python VM.");
		return -1;
	}

	return 0;
}

/*
 * Import modules embedded in the archive - return 0 on success
 */
int pyi_pylib_import_modules(ARCHIVE_STATUS *status)
{
	PyObject *marshal;
	PyObject *marshaldict;
	PyObject *loadfunc;
	TOC *ptoc;
	PyObject *co;
	PyObject *mod;

	VS("importing modules from CArchive\n");

	/* Get the Python function marshall.load
		* Here we collect some reference to PyObject that we don't dereference
		* Doesn't matter because the objects won't be going away anyway.
		*/
	marshal = PI_PyImport_ImportModule("marshal");
	marshaldict = PI_PyModule_GetDict(marshal);
	loadfunc = PI_PyDict_GetItemString(marshaldict, "loads");

	/* Iterate through toc looking for module entries (type 'm')
		* this is normally just bootstrap stuff (archive and iu)
		*/
	ptoc = status->tocbuff;
	while (ptoc < status->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_PYMODULE || ptoc->typcd == ARCHIVE_ITEM_PYPACKAGE)
		{
			unsigned char *modbuf = extract(status, ptoc);

			VS("extracted %s\n", ptoc->name);

			/* .pyc/.pyo files have 8 bytes header. Skip it and load marshalled
			 * data form the right point.
			 */
			co = PI_PyObject_CallFunction(loadfunc, "s#", modbuf+8, ntohl(ptoc->ulen)-8);
			mod = PI_PyImport_ExecCodeModule(ptoc->name, co);

			/* Check for errors in loading */
			if (mod == NULL) {
				FATALERROR("mod is NULL - %s", ptoc->name);
			}
			if (PI_PyErr_Occurred())
			{
				PI_PyErr_Print();
				PI_PyErr_Clear();
			}

			free(modbuf);
		}
		ptoc = incrementTocPtr(status, ptoc);
	}

	return 0;
}


/* Install a zlib from a toc entry
 * Return non zero on failure
 */
int pyi_pylib_install_zlib(ARCHIVE_STATUS *status, TOC *ptoc)
{
	int rc;
	int zlibpos = status->pkgstart + ntohl(ptoc->pos);
	char *tmpl = "sys.path.append(r\"%s?%d\")\n";
	char *cmd = (char *) malloc(strlen(tmpl) + strlen(status->archivename) + 32);
	sprintf(cmd, tmpl, status->archivename, zlibpos);
	/*VS(cmd);*/
	rc = PI_PyRun_SimpleString(cmd);
	if (rc != 0)
	{
		FATALERROR("Error in command: %s\n", cmd);
		free(cmd);
		return -1;
	}

	free(cmd);
	return 0;
}


/*
 * Install zlibs
 * Return non zero on failure
 */
int pyi_pylib_install_zlibs(ARCHIVE_STATUS *status)
{
	TOC * ptoc;
	VS("Installing import hooks\n");

	/* Iterate through toc looking for zlibs (type 'z') */
	ptoc = status->tocbuff;
	while (ptoc < status->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_PYZ)
		{
			VS("%s\n", ptoc->name);
			pyi_pylib_install_zlib(status, ptoc);
		}

		ptoc = incrementTocPtr(status, ptoc);
	}
	return 0;
}

/* decompress data in buff, described by ptoc
 * return in malloc'ed buffer (needs to be freed)
 */
unsigned char *decompress(unsigned char * buff, TOC *ptoc)
{
	const char *ver;
	unsigned char *out;
	z_stream zstream;
	int rc;

	ver = (zlibVersion)();
	out = (unsigned char *)malloc(ntohl(ptoc->ulen));
	if (out == NULL) {
		OTHERERROR("Error allocating decompression buffer\n");
		return NULL;
	}

	zstream.zalloc = NULL;
	zstream.zfree = NULL;
	zstream.opaque = NULL;
	zstream.next_in = buff;
	zstream.avail_in = ntohl(ptoc->len);
	zstream.next_out = out;
	zstream.avail_out = ntohl(ptoc->ulen);
	rc = inflateInit(&zstream);
	if (rc >= 0) {
		rc = (inflate)(&zstream, Z_FINISH);
		if (rc >= 0) {
			rc = (inflateEnd)(&zstream);
		}
		else {
			OTHERERROR("Error %d from inflate: %s\n", rc, zstream.msg);
			return NULL;
		}
	}
	else {
		OTHERERROR("Error %d from inflateInit: %s\n", rc, zstream.msg);
		return NULL;
	}

	return out;
}

/*
 * extract an archive entry
 * returns pointer to the data (must be freed)
 */
unsigned char *extract(ARCHIVE_STATUS *status, TOC *ptoc)
{
	unsigned char *data;
	unsigned char *tmp;

	fseek(status->fp, status->pkgstart + ntohl(ptoc->pos), SEEK_SET);
	data = (unsigned char *)malloc(ntohl(ptoc->len));
	if (data == NULL) {
		OTHERERROR("Could not allocate read buffer\n");
		return NULL;
	}
	if (fread(data, ntohl(ptoc->len), 1, status->fp) < 1) {
	    OTHERERROR("Could not read from file\n");
	    return NULL;
	}
	if (ptoc->cflag == '\2') {
        static PyObject *AES = NULL;
		PyObject *func_new;
		PyObject *aes_dict;
		PyObject *aes_obj;
		PyObject *ddata;
		long block_size;
		char *iv;

		if (!AES)
			AES = PI_PyImport_ImportModule("AES");
		aes_dict = PI_PyModule_GetDict(AES);
		func_new = PI_PyDict_GetItemString(aes_dict, "new");
		block_size = PI_PyInt_AsLong(PI_PyDict_GetItemString(aes_dict, "block_size"));
		iv = malloc(block_size);
		memset(iv, 0, block_size);

		aes_obj = PI_PyObject_CallFunction(func_new, "s#Os#",
			data, 32,
			PI_PyDict_GetItemString(aes_dict, "MODE_CFB"),
			iv, block_size);

		ddata = PI_PyObject_CallMethod(aes_obj, "decrypt", "s#", data+32, ntohl(ptoc->len)-32);
		memcpy(data, PI_PyString_AsString(ddata), ntohl(ptoc->len)-32);
		Py_DECREF(aes_obj);
		Py_DECREF(ddata);
		VS("decrypted %s\n", ptoc->name);
	}
	if (ptoc->cflag == '\1' || ptoc->cflag == '\2') {
		tmp = decompress(data, ptoc);
		free(data);
		data = tmp;
		if (data == NULL) {
			OTHERERROR("Error decompressing %s\n", ptoc->name);
			return NULL;
		}
	}
	return data;
}


/*
 * extract from the archive
 * and copy to the filesystem
 * relative to the directory the archive's in
 */
int extract2fs(ARCHIVE_STATUS *status, TOC *ptoc)
{
	FILE *out;
	unsigned char *data = extract(status, ptoc);

    if (pyi_create_temp_path(status) == -1){
        return -1;
    }

	out = pyi_open_target(status->temppath, ptoc->name);

	if (out == NULL)  {
		FATALERROR("%s could not be extracted!\n", ptoc->name);
		return -1;
	}
	else {
		fwrite(data, ntohl(ptoc->ulen), 1, out);
#ifndef WIN32
		fchmod(fileno(out), S_IRUSR | S_IWUSR | S_IXUSR);
#endif
		fclose(out);
	}
	free(data);
	return 0;
}

/* Splits the item in the form path:filename */
static int splitName(char *path, char *filename, const char *item)
{
    char name[PATH_MAX + 1];

    VS("Splitting item into path and filename\n");
    strcpy(name, item);
    strcpy(path, strtok(name, ":"));
    strcpy(filename, strtok(NULL, ":")) ;

    if (path[0] == 0 || filename[0] == 0)
        return -1;
    return 0;
}

/* Copy the dependencies file from a directory to the tempdir */
static int copyDependencyFromDir(ARCHIVE_STATUS *status, const char *srcpath, const char *filename)
{
    if (pyi_create_temp_path(status) == -1){
        return -1;
    }

    VS("Coping file %s to %s\n", srcpath, status->temppath);
    if (pyi_copy_file(srcpath, status->temppath, filename) == -1) {
        return -1;
    }
    return 0;
}

/* Look for the archive identified by path into the ARCHIVE_STATUS pool status_list.
 * If the archive is found, a pointer to the associated ARCHIVE_STATUS is returned
 * otherwise the needed archive is opened and added to the pool and then returned.
 * If an error occurs, returns NULL.
 */
static ARCHIVE_STATUS *get_archive(ARCHIVE_STATUS *status_list[], const char *path)
{
    ARCHIVE_STATUS *status = NULL;
    int i = 0;

    VS("Getting file from archive.\n");
    if (pyi_create_temp_path(status_list[SELF]) == -1){
        return NULL;
    }

    for (i = 1; status_list[i] != NULL; i++){
        if (strcmp(status_list[i]->archivename, path) == 0) {
            VS("Archive found: %s\n", path);
            return status_list[i];
        }
        VS("Checking next archive in the list...\n");
    }

    if ((status = (ARCHIVE_STATUS *) calloc(1, sizeof(ARCHIVE_STATUS))) == NULL) {
        FATALERROR("Error allocating memory for status\n");
        return NULL;
    }

    strcpy(status->archivename, path);
    strcpy(status->homepath, status_list[SELF]->homepath);
    strcpy(status->temppath, status_list[SELF]->temppath);
#ifdef WIN32
    strcpy(status->homepathraw, status_list[SELF]->homepathraw);
    strcpy(status->temppathraw, status_list[SELF]->temppathraw);
#endif

    if (pyi_arch_open(status)) {
        FATALERROR("Error openning archive %s\n", path);
        free(status);
        return NULL;
    }

    status_list[i] = status;
    return status;
}

/* Extract a file identifed by filename from the archive associated to status. */
static int extractDependencyFromArchive(ARCHIVE_STATUS *status, const char *filename)
{
	TOC * ptoc = status->tocbuff;
	VS("Extracting dependencies from archive\n");
	while (ptoc < status->tocend) {
		if (strcmp(ptoc->name, filename) == 0)
			if (extract2fs(status, ptoc))
				return -1;
		ptoc = incrementTocPtr(status, ptoc);
	}
	return 0;
}

/* Decide if the dependency identified by item is in a onedir or onfile archive
 * then call the appropriate function.
 */
static int extractDependency(ARCHIVE_STATUS *status_list[], const char *item)
{
    ARCHIVE_STATUS *status = NULL;
    char path[PATH_MAX + 1];
    char filename[PATH_MAX + 1];
    char srcpath[PATH_MAX + 1];
    char archive_path[PATH_MAX + 1];

    char *dirname = NULL;

    VS("Extracting dependencies\n");
    if (splitName(path, filename, item) == -1)
        return -1;

    dirname = pyi_path_dirname(path);
    if (dirname[0] == 0) {
        free(dirname);
        return -1;
    }

    /* We need to identify three situations: 1) dependecies are in a onedir archive
     * next to the current onefile archive, 2) dependencies are in a onedir/onefile
     * archive next to the current onedir archive, 3) dependencies are in a onefile
     * archive next to the current onefile archive.
     */
    VS("Checking if file exists\n");
    if (checkFile(srcpath, "%s/%s/%s", status_list[SELF]->homepath, dirname, filename) == 0) {
        VS("File %s found, assuming is onedir\n", srcpath);
        if (copyDependencyFromDir(status_list[SELF], srcpath, filename) == -1) {
            FATALERROR("Error coping %s\n", filename);
            free(dirname);
            return -1;
        }
    } else if (checkFile(srcpath, "%s../%s/%s", status_list[SELF]->homepath, dirname, filename) == 0) {
        VS("File %s found, assuming is onedir\n", srcpath);
        if (copyDependencyFromDir(status_list[SELF], srcpath, filename) == -1) {
            FATALERROR("Error coping %s\n", filename);
            free(dirname);
            return -1;
        }
    } else {
        VS("File %s not found, assuming is onefile.\n", srcpath);
        if ((checkFile(archive_path, "%s%s.pkg", status_list[SELF]->homepath, path) != 0) &&
            (checkFile(archive_path, "%s%s.exe", status_list[SELF]->homepath, path) != 0) &&
            (checkFile(archive_path, "%s%s", status_list[SELF]->homepath, path) != 0)) {
            FATALERROR("Archive not found: %s\n", archive_path);
            return -1;
        }

        if ((status = get_archive(status_list, archive_path)) == NULL) {
            FATALERROR("Archive not found: %s\n", archive_path);
            return -1;
        }
        if (extractDependencyFromArchive(status, filename) == -1) {
            FATALERROR("Error extracting %s\n", filename);
            free(status);
            return -1;
        }
    }
    free(dirname);

    return 0;
}


/*
 * check if binaries need to be extracted. If not, this is probably a onedir solution,
 * and a child process will not be required on windows.
 */
int needToExtractBinaries(ARCHIVE_STATUS *status_list[])
{
	TOC * ptoc = status_list[SELF]->tocbuff;
	while (ptoc < status_list[SELF]->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_BINARY || ptoc->typcd == ARCHIVE_ITEM_DATA ||
                ptoc->typcd == ARCHIVE_ITEM_ZIPFILE)
            return true;
        if (ptoc->typcd == ARCHIVE_ITEM_DEPENDENCY) {
            return true;
        }
		ptoc = incrementTocPtr(status_list[SELF], ptoc);
	}
	return false;
}

/*
 * extract all binaries (type 'b') and all data files (type 'x') to the filesystem
 * and checks for dependencies (type 'd'). If dependencies are found, extract them.
 */
int extractBinaries(ARCHIVE_STATUS *status_list[])
{
	TOC * ptoc = status_list[SELF]->tocbuff;
	VS("Extracting binaries\n");
	while (ptoc < status_list[SELF]->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_BINARY || ptoc->typcd == ARCHIVE_ITEM_DATA ||
                ptoc->typcd == ARCHIVE_ITEM_ZIPFILE)
			if (extract2fs(status_list[SELF], ptoc))
				return -1;

        if (ptoc->typcd == ARCHIVE_ITEM_DEPENDENCY) {
            if (extractDependency(status_list, ptoc->name) == -1)
                return -1;
        }
		ptoc = incrementTocPtr(status_list[SELF], ptoc);
	}
	return 0;
}

/*
 * Run scripts
 * Return non zero on failure
 */
int pyi_pylib_run_scripts(ARCHIVE_STATUS *status)
{
	unsigned char *data;
	char buf[PATH_MAX];
	int rc = 0;
	TOC * ptoc = status->tocbuff;
	PyObject *__main__ = PI_PyImport_AddModule("__main__");
	PyObject *__file__;
	VS("Running scripts\n");

	/* Iterate through toc looking for scripts (type 's') */
	while (ptoc < status->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_PYSOURCE) {
			/* Get data out of the archive.  */
			data = extract(status, ptoc);
			/* Set the __file__ attribute within the __main__ module,
			   for full compatibility with normal execution. */
			strcpy(buf, ptoc->name);
			strcat(buf, ".py");
            __file__ = PI_PyString_FromStringAndSize(buf, strlen(buf));
            PI_PyObject_SetAttrString(__main__, "__file__", __file__);
            Py_DECREF(__file__);
			/* Run it */
			rc = PI_PyRun_SimpleString((char *) data);
			/* log errors and abort */
			if (rc != 0) {
				VS("RC: %d from %s\n", rc, ptoc->name);
				return rc;
			}
			free(data);
		}

		ptoc = incrementTocPtr(status, ptoc);
	}
	return 0;
}

/*
 * call a simple "int func(void)" entry point.  Assumes such a function
 * exists in the main namespace.
 * Return non zero on failure, with -2 if the specific error is
 * that the function does not exist in the namespace.
 */
int callSimpleEntryPoint(char *name, int *presult)
{
	int rc = -1;
	/* Objects with no ref. */
	PyObject *mod, *dict;
	/* Objects with refs to kill. */
	PyObject *func = NULL, *pyresult = NULL;

	mod = PI_PyImport_AddModule("__main__"); /* NO ref added */
	if (!mod) {
		VS("No __main__\n");
		goto done;
	}
	dict = PI_PyModule_GetDict(mod); /* NO ref added */
	if (!mod) {
		VS("No __dict__\n");
		goto done;
	}
	func = PI_PyDict_GetItemString(dict, name);
	if (func == NULL) { /* should explicitly check KeyError */
		VS("CallSimpleEntryPoint can't find the function name\n");
		rc = -2;
		goto done;
	}
	pyresult = PI_PyObject_CallFunction(func, "");
	if (pyresult==NULL) goto done;
	PI_PyErr_Clear();
	*presult = PI_PyInt_AsLong(pyresult);
	rc = PI_PyErr_Occurred() ? -1 : 0;
	VS( rc ? "Finished with failure\n" : "Finished OK\n");
	/* all done! */
done:
	Py_XDECREF(func);
	Py_XDECREF(pyresult);
	/* can't leave Python error set, else it may
	   cause failures in later async code */
	if (rc)
		/* But we will print them 'cos they may be useful */
		PI_PyErr_Print();
	PI_PyErr_Clear();
	return rc;
}

/* for finer grained control */
/*
 * initialize (this always needs to be done)
 */
int init(ARCHIVE_STATUS *status, char const * archivePath, char  const * archiveName)
{
	/* Set up paths */
	if (pyi_arch_set_paths(status, archivePath, archiveName))
		return -1;

	/* Open the archive */
	if (pyi_arch_open(status))
		return -1;

	return 0;
}

/*
 * Once init'ed, you might want to extractBinaries()
 * If you do, what comes after is very platform specific.
 * Once you've taken care of the platform specific details,
 * or if there are no binaries to extract, you go on
 * to doIt(), which is the important part.
 */
int doIt(ARCHIVE_STATUS *status, int argc, char *argv[])
{
	int rc = 0;
	/* Load Python DLL */
	if (pyi_pylib_load(status))
		return -1;

	/* Start Python. */
	if (pyi_pylib_start_python(status, argc, argv))
		return -1;

	/* Import modules from archive - bootstrap */
	if (pyi_pylib_import_modules(status))
		return -1;

	/* Install zlibs  - now all hooks in place */
	if (pyi_pylib_install_zlibs(status))
		return -1;

	/* Run scripts */
	rc = pyi_pylib_run_scripts(status);

	VS("OK.\n");

	return rc;
}

/*
 * Helpers for embedders
 */
int pyi_arch_get_pyversion(ARCHIVE_STATUS *status)
{
	return ntohl(status->cookie.pyvers);
}

void pyi_pylib_finalize(void)
{
	PI_Py_Finalize();
}
