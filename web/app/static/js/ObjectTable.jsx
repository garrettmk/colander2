import React from "react";
import update from "immutability-helper";
import _ from "lodash";
import { Segment, Table, Select, Menu, Icon, Pagination } from "semantic-ui-react";

import Colander from "./colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default class ObjectTable extends React.Component {

    constructor (props) {
        super(props);

        this.fetchObjects = this.fetchObjects.bind(this);
        this.handleColumnClick = this.handleColumnClick.bind(this);

        this.state = {
            loading: false,
            items: [],
        }
    }

    componentDidMount () { this.fetchObjects() }

    componentDidUpdate (prevProps, prevState) {
        if (!_.isEqual(prevProps.query, this.props.query)
            || !_.isEqual(prevProps.view, this.props.view)) {
            this.fetchObjects();
        }
    }

    fetchObjects () {
        this.setState({ loading: true });
        const { type, query, view = {} } = this.props;

        Colander.filter(type, {
            query,
            view,

            onSuccess: results => { this.setState({ loading: false, ...results }) },

            onFailure: error => {
                alert(error);
                this.setState({ loading: false });
            }
        })
    }

    handleColumnClick (idx) {
        const column = this.props.columns[idx];
        if (column.onClick)
            column.onClick(column);
    }

    render () {
        const { loading, items } = this.state;
        const { columns } = this.props;

        const formattedColumns = columns.map((col, idx) => {
            const addedStyle = {};

            if (idx === 0)
                addedStyle.paddingLeft = '2em';
            if (idx === columns.length - 1)
                addedStyle.paddingRight = '2em';

            return update(col, {
                format: format => update(format || {}, {
                    style: style => update(style || {}, {$merge: addedStyle}),
                })
            });
        });

        return (
            <Segment raised loading={loading} style={{ padding: 0 }}>
                <Table selectable sortable striped basic={'very'}>

                    <Table.Header>
                        <Table.Row>
                            {formattedColumns.map((column, idx) => {
                                const { label, format } = column;
                                return <Table.HeaderCell
                                    key={label}
                                    onClick={() => this.handleColumnClick(idx)}
                                    {...format}
                                >
                                    {label}
                                </Table.HeaderCell>;
                            })}
                        </Table.Row>
                    </Table.Header>

                    <Table.Body>
                        {items.map(obj => (
                            <Table.Row key={obj.id}>
                                {formattedColumns.map(column => {
                                    const { label, value, format } = column;
                                    return (
                                        <Table.Cell key={label} {...format}>
                                            {typeof value === 'string'
                                                ? obj[value]
                                                : value(obj)
                                            }
                                        </Table.Cell>
                                    )
                                })}
                            </Table.Row>
                        ))}
                    </Table.Body>

                    {/*<Table.Footer>*/}
                        {/*<Table.Row>*/}
                            {/*<Table.HeaderCell colSpan={columns.length} textAlign={'right'}>*/}
                                {/*{total} results.*/}
                                {/*<Pagination*/}
                                    {/*activePage={page}*/}
                                    {/*onPageChange={this.handlePageChange}*/}
                                    {/*totalPages={pages}*/}
                                {/*/>*/}
                            {/*</Table.HeaderCell>*/}
                        {/*</Table.Row>*/}
                    {/*</Table.Footer>*/}

                </Table>
            </Segment>
        )
    }
}