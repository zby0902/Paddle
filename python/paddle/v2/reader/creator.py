# Copyright (c) 2016 PaddlePaddle Authors. All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Creator package contains some simple reader creator, which could
be used in user program.
"""

__all__ = ['np_array', 'text_file', "cloud_reader"]


def np_array(x):
    """
    Creates a reader that yields elements of x, if it is a
    numpy vector. Or rows of x, if it is a numpy matrix.
    Or any sub-hyperplane indexed by the highest dimension.

    :param x: the numpy array to create reader from.
    :returns: data reader created from x.
    """

    def reader():
        if x.ndim < 1:
            yield x

        for e in x:
            yield e

    return reader


def text_file(path):
    """
    Creates a data reader that outputs text line by line from given text file.
    Trailing new line ('\\\\n') of each line will be removed.

    :path: path of the text file.
    :returns: data reader of text file
    """

    def reader():
        f = open(path, "r")
        for l in f:
            yield l.rstrip('\n')
        f.close()

    return reader


def recordio(paths, buf_size=100):
    """
    Creates a data reader from given RecordIO file paths separated by ",",
        glob pattern is supported.
    :path: path of recordio files, can be a string or a string list.
    :returns: data reader of recordio files.
    """

    import recordio as rec
    import paddle.v2.reader.decorator as dec
    import cPickle as pickle

    def reader():
        if isinstance(paths, basestring):
            path = paths
        else:
            path = ",".join(paths)
        f = rec.reader(path)
        while True:
            r = f.read()
            if r is None:
                break
            yield pickle.loads(r)
        f.close()

    return dec.buffered(reader, buf_size)


pass_num = 0


def cloud_reader(paths, etcd_endpoints, timeout_sec=5, buf_size=64):
    """
    Create a data reader that yield a record one by one from
        the paths:
    :paths: path of recordio files, can be a string or a string list.
    :etcd_endpoints: the endpoints for etcd cluster
    :returns: data reader of recordio files.

    ..  code-block:: python
        from paddle.v2.reader.creator import cloud_reader
        etcd_endpoints = "http://127.0.0.1:2379"
        trainer.train.(
            reader=cloud_reader(["/work/dataset/uci_housing/uci_housing*"], etcd_endpoints),
        )
    """
    import os
    import cPickle as pickle
    import paddle.v2.master as master
    c = master.client(etcd_endpoints, timeout_sec, buf_size)

    if isinstance(paths, basestring):
        path = [paths]
    else:
        path = paths
    c.set_dataset(path)

    def reader():
        global pass_num
        c.paddle_start_get_records(pass_num)
        pass_num += 1

        while True:
            r, e = c.next_record()
            if not r:
                if e != -2:
                    print "get record error: ", e
                break
            yield pickle.loads(r)

    return reader
