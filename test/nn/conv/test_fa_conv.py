import torch

import torch_geometric.typing
from torch_geometric.nn import FAConv
from torch_geometric.testing import is_full_test
from torch_geometric.typing import SparseTensor
from torch_geometric.utils import to_torch_csc_tensor


def test_fa_conv():
    x = torch.randn(4, 16)
    x_0 = torch.randn(4, 16)
    edge_index = torch.tensor([[0, 0, 0, 1, 2, 3], [1, 2, 3, 0, 0, 0]])
    adj1 = to_torch_csc_tensor(edge_index, size=(4, 4))

    # adj1 = SparseTensor(row=row, col=col, sparse_sizes=(4, 4))

    conv = FAConv(16, eps=1.0, cached=True)
    assert str(conv) == 'FAConv(16, eps=1.0)'
    out = conv(x, x_0, edge_index)
    assert conv._cached_edge_index is not None
    assert out.size() == (4, 16)

    if torch_geometric.typing.WITH_TORCH_SPARSE:
        adj2 = SparseTensor.from_edge_index(edge_index, sparse_sizes=(4, 4))
        assert torch.allclose(conv(x, x_0, adj2.t()), out)
        assert conv._cached_adj_t is not None
        assert torch.allclose(conv(x, x_0, adj2.t()), out)

    if is_full_test():
        jit = torch.jit.script(conv.jittable())
        assert torch.allclose(jit(x, x_0, edge_index), out)

        if torch_geometric.typing.WITH_TORCH_SPARSE:
            assert torch.allclose(jit(x, x_0, adj2.t()), out)

    conv.reset_parameters()
    assert conv._cached_edge_index is None
    assert conv._cached_adj_t is None

    # Test without caching:
    conv.cached = False
    out = conv(x, x_0, edge_index)
    assert torch.allclose(conv(x, x_0, adj1.t()), out)
    if torch_geometric.typing.WITH_TORCH_SPARSE:
        assert torch.allclose(conv(x, x_0, adj2.t()), out)

    # Test `return_attention_weights`:
    result = conv(x, x_0, edge_index, return_attention_weights=True)
    assert torch.allclose(result[0], out)
    assert result[1][0].size() == (2, 10)
    assert result[1][1].size() == (10, )
    assert conv._alpha is None

    result = conv(x, x_0, adj1.t(), return_attention_weights=True)
    assert torch.allclose(result[0], out)
    assert result[1][0].size() == torch.Size([4, 4])
    assert result[1][0]._nnz() == 10
    assert conv._alpha is None

    if torch_geometric.typing.WITH_TORCH_SPARSE:
        result = conv(x, x_0, adj2.t(), return_attention_weights=True)
        assert torch.allclose(result[0], out)
        assert result[1].sizes() == [4, 4] and result[1].nnz() == 10
        assert conv._alpha is None

    if is_full_test():
        jit = torch.jit.script(conv.jittable())
        result = jit(x, x_0, edge_index, return_attention_weights=True)
        assert torch.allclose(result[0], out)
        assert result[1][0].size() == (2, 10)
        assert result[1][1].size() == (10, )
        assert conv._alpha is None

        if torch_geometric.typing.WITH_TORCH_SPARSE:
            result = jit(x, x_0, adj2.t(), return_attention_weights=True)
            assert torch.allclose(result[0], out)
            assert result[1].sizes() == [4, 4] and result[1].nnz() == 10
            assert conv._alpha is None
