import React from "react";

import { Segment, Image, Header, Icon, Message, Loader } from "semantic-ui-react";

import { DocumentContext } from "../Context/DocumentContext";
import { defaultImages } from "../style";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const headerOpts = {
    style: {
        whiteSpace: 'nowrap',
        textOverflow: 'ellipsis',
        overflow: 'hidden',
        display: 'block',
    }
};


const headerImgOpts = {
    size: 'small',
    centered: true,
    rounded: true,
    style: {
        display: 'block'
    }
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default function ObjectHeader (props) {
    let { as, ...containerProps } = props;

    if (!as) {
        as = Segment;
        if (containerProps.raised === undefined)
            containerProps.raised = true;
    }

    return (
        <DocumentContext.Consumer>
            {({ loading, preview }) => {
                let children;

                if (loading)
                    children = <Loader active={true}/>;
                else if (!preview)
                    children = <Message error>No data :(</Message>;
                else
                    children = (
                        <React.Fragment>
                            <Image src={preview.image || defaultImages[preview.type]} href={preview.url} {...headerImgOpts}/>
                            <Header {...headerOpts}>
                                {preview.title}
                                <Header.Subheader>
                                    <a href={preview.url} target={'_blank'}>{preview.description} <Icon name={'external'}/></a>
                                </Header.Subheader>
                            </Header>
                        </React.Fragment>
                    );

                return React.createElement(as, containerProps, children);
            }}
        </DocumentContext.Consumer>
    )
}
