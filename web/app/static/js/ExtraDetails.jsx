import React from "react";
import Colander from "./colander";

import { Segment, Header, Message } from "semantic-ui-react";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default class ExtraDetails extends React.Component {

    constructor (props) {
        super(props);

        this.state = {
            loading: true,
            data: {},
            error: undefined
        }
    }

    componentDidMount () {
        this.setState({ loading: true });
        const { type, id } = this.props;

        Colander.filter(type, {
            query: { id },
            view: { _only: ['extra'] },

            onSuccess: results => { this.setState({ loading: false, error: undefined, data: results.items[0].extra }) },
            onFailure: error => { this.setState({ loading: false, error: error })}
        });
    }

    render () {
        const { loading, data, error } = this.state;

        return (
            <Segment raised loading={loading}>
                <Header size={'small'} dividing>Extra</Header>
                {error
                    ? <Message error>{error}</Message>
                    : <pre style={{ overflow: 'auto' }}>{JSON.stringify(data, null, '  ')}</pre>
                }
            </Segment>
        )
    }
}
