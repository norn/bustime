#include <Python.h>
#include "cdistance.h"

// http://dan.iel.fm/posts/python-c-extensions/
// git clone git://gist.github.com/3247796.git c_ext

static char module_docstring[] =
    "This module provides an interface for calculating chi-squared using C.";
static char cdistance_docstring[] =
    "Calculate the chi-squared of some data given a model.";

/* Available functions */
static PyObject *cdistance_cdistance(PyObject *self, PyObject *args);

/* Module specification */
static PyMethodDef module_methods[] = {
    {"cdistance", cdistance_cdistance, METH_VARARGS, cdistance_docstring},
    {NULL, NULL, 0, NULL}
};

/* Initialize the module */
// PyMODINIT_FUNC init_cdistance(void)
// {
//     PyObject *m = Py_InitModule3("_cdistance", module_methods, module_docstring);
// }

static struct PyModuleDef cdistance = 
{
    PyModuleDef_HEAD_INIT, 
    "cdistance", /* name of module */
    "usage: cdistance.cdistance(lon1, lat1, lon2, lat2)\n",
    -1,
    module_methods
};

PyMODINIT_FUNC PyInit__cdistance(void)
{
    return PyModule_Create(&cdistance);
}

static PyObject *cdistance_cdistance(PyObject *self, PyObject *args)
{
    double lon1,lat1,lon2,lat2;
    if (!PyArg_ParseTuple(args, "dddd", &lon1, &lat1, &lon2, &lat2))
        return NULL;

    long int dist = distance(lon1 ,lat1, lon2, lat2);
    /* Build the output tuple */
    // https://docs.python.org/2/c-api/arg.html#c.Py_BuildValue
    // PyObject *ret = Py_BuildValue("f", dist); // float
    PyObject *ret = Py_BuildValue("l", dist); // unsigned long 
    return ret;
}