/*
 * Launch a python module from an archive.
 *
 * Copyright (C) 2005, Giovanni Bajo
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
#ifndef LAUNCH_H
#define LAUNCH_H

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#ifdef WIN32
#include <io.h>
#else
#include <unistd.h>
#endif
#include <fcntl.h>
#ifdef WIN32
#include <winsock.h> /* for ntohl */
#else
#include <netinet/in.h>
#endif

#include "pyi_archive.h"
#include "pyi_global.h"

/* We use dynamic loading so one binary
   can be used with (nearly) any Python version.
   This is the cruft necessary to do dynamic loading
*/

/*
 * These macros used to define variables to hold dynamically accessed entry
 * points. These are declared 'extern' in this header, and defined fully later.
 */
#ifdef WIN32

#define EXTDECLPROC(result, name, args)\
    typedef result (__cdecl *__PROC__##name) args;\
    extern __PROC__##name PI_##name;

#define EXTDECLVAR(vartyp, name)\
    typedef vartyp __VAR__##name;\
    extern __VAR__##name *PI_##name;

#else

#define EXTDECLPROC(result, name, args)\
    typedef result (*__PROC__##name) args;\
    extern __PROC__##name PI_##name;

#define EXTDECLVAR(vartyp, name)\
    typedef vartyp __VAR__##name;\
    extern __VAR__##name *PI_##name;

#endif /* WIN32 */

/*
 * Python.h replacements.
 *
 * We do not want to include Python.h because we do no want to bind
 * to a specific version of Python. If we were to, eg., use the 
 * Py_INCREF macro from Python.h, the compiled code would depend
 * on the specific layout in memory of PyObject, and thus change
 * when Python changes (or if your platform changes between 32bit
 * and 64bit). In other words, you wouldn't be able to build a single
 * bootloader working across all Python versions (which is specifically
 * important on Windows).
 *
 * Instead, the bootloader does not depend on the Python ABI at all.
 * It dynamically-load the Python library (after having unpacked it)
 * and bind the exported functions. All Python objects are used as
 * opaque data structures (through pointers only), so the code is
 * fully compatible if the Python data structure layouts change.
 */

/* Forward declarations of opaque Python types. */
struct _object;
typedef struct _object PyObject;
struct _PyThreadState;
typedef struct _PyThreadState PyThreadState;

/* The actual declarations of var & function entry points used. */
EXTDECLVAR(int, Py_FrozenFlag);
EXTDECLVAR(int, Py_NoSiteFlag);
EXTDECLVAR(int, Py_OptimizeFlag);
EXTDECLVAR(int, Py_VerboseFlag);
EXTDECLPROC(int, Py_Initialize, (void));
EXTDECLPROC(int, Py_Finalize, (void));
EXTDECLPROC(void, Py_IncRef, (PyObject *));
EXTDECLPROC(void, Py_DecRef, (PyObject *));
EXTDECLPROC(void, Py_SetPythonHome, (char *));
EXTDECLPROC(PyObject *, PyImport_ExecCodeModule, (char *, PyObject *));
EXTDECLPROC(int, PyRun_SimpleString, (char *));
EXTDECLPROC(int, PySys_SetArgv, (int, char **));
EXTDECLPROC(void, Py_SetProgramName, (char *));
EXTDECLPROC(PyObject *, PyImport_ImportModule, (char *));
EXTDECLPROC(PyObject *, PyImport_AddModule, (char *));
EXTDECLPROC(int, PyObject_SetAttrString, (PyObject *, char *, PyObject *));
EXTDECLPROC(PyObject *, PyList_New, (int));
EXTDECLPROC(int, PyList_Append, (PyObject *, PyObject *));
EXTDECLPROC(PyObject *, Py_BuildValue, (char *, ...));
EXTDECLPROC(PyObject *, PyString_FromStringAndSize, (const char *, int));
EXTDECLPROC(PyObject *, PyFile_FromString, (char *, char *));
EXTDECLPROC(char *, PyString_AsString, (PyObject *));
EXTDECLPROC(PyObject *, PyObject_CallFunction, (PyObject *, char *, ...));
EXTDECLPROC(PyObject *, PyModule_GetDict, (PyObject *));
EXTDECLPROC(PyObject *, PyDict_GetItemString, (PyObject *, char *));
EXTDECLPROC(void, PyErr_Clear, (void) );
EXTDECLPROC(PyObject *, PyErr_Occurred, (void) );
EXTDECLPROC(void, PyErr_Print, (void) );
EXTDECLPROC(PyObject *, PyObject_CallObject, (PyObject *, PyObject*) );
EXTDECLPROC(PyObject *, PyObject_CallMethod, (PyObject *, char *, char *, ...) );
EXTDECLPROC(void, PySys_AddWarnOption, (char *));
EXTDECLPROC(void, PyEval_InitThreads, (void) );
EXTDECLPROC(void, PyEval_AcquireThread, (PyThreadState *) );
EXTDECLPROC(void, PyEval_ReleaseThread, (PyThreadState *) );
EXTDECLPROC(PyThreadState *, PyThreadState_Swap, (PyThreadState *) );
EXTDECLPROC(PyThreadState *, Py_NewInterpreter, (void) );
EXTDECLPROC(void, Py_EndInterpreter, (PyThreadState *) );
EXTDECLPROC(long, PyInt_AsLong, (PyObject *) );
EXTDECLPROC(int, PySys_SetObject, (char *, PyObject *));


/* 
 * Macros for reference counting through exported functions
 * (that is: without binding to the binary structure of a PyObject.
 * These rely on the Py_IncRef/Py_DecRef API functions on Pyhton 2.4+.
 *
 * Python versions before 2.4 do not export IncRef/DecRef as a binary API,
 * but only as macros in header files. Since we support Python 2.4+ we do not
 * need to provide an emulated incref/decref as it was with older Python
 * versions.
 *
 * We do not want to depend on Python.h for many reasons (including the fact
 * that we would like to have a single binary for all Python versions).
 */

#define Py_XINCREF(o)    PI_Py_IncRef(o)
#define Py_XDECREF(o)    PI_Py_DecRef(o)
#define Py_DECREF(o)     Py_XDECREF(o)
#define Py_INCREF(o)     Py_XINCREF(o)

/* Macros to declare and get Python entry points in the C file.
 * Typedefs '__PROC__...' have been done above
 */
#ifdef WIN32

#define DECLPROC(name)\
    __PROC__##name PI_##name = NULL;
#define GETPROCOPT(dll, name)\
    PI_##name = (__PROC__##name)GetProcAddress (dll, #name)
#define GETPROC(dll, name)\
    GETPROCOPT(dll, name); \
    if (!PI_##name) {\
        FATALERROR ("Cannot GetProcAddress for " #name);\
        return -1;\
    }
#define DECLVAR(name)\
    __VAR__##name *PI_##name = NULL;
#define GETVAR(dll, name)\
    PI_##name = (__VAR__##name *)GetProcAddress (dll, #name);\
    if (!PI_##name) {\
        FATALERROR ("Cannot GetProcAddress for " #name);\
        return -1;\
    }

#else

#define DECLPROC(name)\
    __PROC__##name PI_##name = NULL;
#define GETPROCOPT(dll, name)\
    PI_##name = (__PROC__##name)dlsym (dll, #name)
#define GETPROC(dll, name)\
    GETPROCOPT(dll, name);\
    if (!PI_##name) {\
        FATALERROR ("Cannot dlsym for " #name);\
        return -1;\
    }
#define DECLVAR(name)\
    __VAR__##name *PI_##name = NULL;
#define GETVAR(dll, name)\
    PI_##name = (__VAR__##name *)dlsym(dll, #name);\
    if (!PI_##name) {\
        FATALERROR ("Cannot dlsym for " #name);\
        return -1;\
    }

#endif /* WIN32 */

/*
 * #defines
 */
#define MAGIC "MEI\014\013\012\013\016"


#define SELF 0

/*****************************************************************
 * The following 4 entries are for applications which may need to
 * use to 2 steps to execute
 *****************************************************************/

/**
 * Initialize the paths and open the archive
 *
 * @param archivePath  The path (with trailing backslash) to the archive.
 *
 * @param archiveName  The file name of the archive, without a path.
 *
 * @param workpath     The path (with trailing backslash) to where
 *                     the binaries were extracted. If they have not
 *                     benn extracted yet, this is NULL. If they have,
 *                     this will either be archivePath, or a temp dir
 *                     where the user has write permissions.
 *
 * @return 0 on success, non-zero otherwise.
 */
int init(ARCHIVE_STATUS *status, char const * archivePath, char  const * archiveName);

/**
 * Extract binaries in the archive
 *
 * @param workpath     (OUT) Where the binaries were extracted to. If
 *                      none extracted, is NULL.
 *
 * @return 0 on success, non-zero otherwise.
 */
int extractBinaries(ARCHIVE_STATUS *status_list[]);

/**
 * Load Python and execute all scripts in the archive
 *
 * @param argc			Count of "commandline" args
 *
 * @param argv			The "commandline".
 *
 * @return -1 for internal failures, or the rc of the last script.
 */
int doIt(ARCHIVE_STATUS *status, int argc, char *argv[]);

/*
 * Call a simple "int func(void)" entry point.  Assumes such a function
 * exists in the main namespace.
 * Return non zero on failure, with -2 if the specific error is
 * that the function does not exist in the namespace.
 *
 * @param name		Name of the function to execute.
 * @param presult	Integer return value.
 */
int callSimpleEntryPoint(char *name, int *presult);

/**
 * Clean up extracted binaries
 */
void cleanUp(ARCHIVE_STATUS *status);

/**
 * Helpers for embedders
 */
int pyi_arch_get_pyversion(ARCHIVE_STATUS *status);
void pyi_pylib_finalize(void);

/**
 * The gory detail level
 */
int pyi_arch_set_paths(ARCHIVE_STATUS *status, char const * archivePath, char const * archiveName);
int pyi_arch_open(ARCHIVE_STATUS *status);
int pyi_pylib_attach(ARCHIVE_STATUS *status, int *loadedNew);
int pyi_pylib_load(ARCHIVE_STATUS *status); /* note - pyi_pylib_attach will call this if not already loaded */
int pyi_pylib_start_python(ARCHIVE_STATUS *status, int argc, char *argv[]);
int pyi_pylib_import_modules(ARCHIVE_STATUS *status);
int pyi_pylib_install_zlibs(ARCHIVE_STATUS *status);
int pyi_pylib_run_scripts(ARCHIVE_STATUS *status);
TOC *getFirstTocEntry(ARCHIVE_STATUS *status);
TOC *getNextTocEntry(ARCHIVE_STATUS *status, TOC *entry);
#endif

