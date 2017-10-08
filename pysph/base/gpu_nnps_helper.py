#!/usr/bin/env python

from pyopencl.elementwise import ElementwiseKernel
from mako.template import Template
import os

from pysph.base.opencl import get_config, profile


class GPUNNPSHelper(object):
    def __init__(self, ctx, tpl_filename, use_double=False):
        self.src_tpl = Template(
            filename=os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                tpl_filename),
            disable_unicode=True
        )

        self.data_t = "double" if use_double else "float"

        helper_tpl = Template(
            filename=os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "gpu_helper_functions.mako"),
            disable_unicode=True
        )

        helper_preamble = helper_tpl.get_def("get_helpers").render(
            data_t=self.data_t
        )
        preamble = self.src_tpl.get_def("preamble").render(
            data_t=self.data_t
        )
        self.preamble = "\n".join([helper_preamble, preamble])
        self.ctx = ctx
        self.cache = {}
        self._profile = get_config().profile

    def _get_code(self, kernel_name, **kwargs):
        arguments = self.src_tpl.get_def("%s_args" % kernel_name).render(
                data_t=self.data_t, **kwargs)

        src = self.src_tpl.get_def("%s_src" % kernel_name).render(
                data_t=self.data_t, **kwargs)

        return arguments, src

    def get_kernel(self, kernel_name, **kwargs):
        data = kernel_name, tuple(kwargs.items())
        if data in self.cache:
            return self.cache[data], kernel_name
        else:
            args, src = self._get_code(kernel_name, **kwargs)
            knl = ElementwiseKernel(
                self.ctx, args, src,
                kernel_name, preamble=self.preamble
            )
            self.cache[data] = knl
            return knl, kernel_name

    def profile_kernel(self, kernel):
        def _profile_knl(*args):
            event = kernel(*args)
            if self._profile:
                profile(kernel.name, event)
        return _profile_knl
